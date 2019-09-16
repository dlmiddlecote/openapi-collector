import logging
import time
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pykube
import yaml
from pytest import fixture


@fixture(scope="session")
def cluster(kind_cluster) -> dict:
    image_prefix = os.getenv("IMAGE_PREFIX")
    image_tag = os.getenv("TAG")

    images = {
        "router": f"{image_prefix}-router:{image_tag}",
        "collector": f"{image_prefix}-collector:{image_tag}",
        "proxy": f"{image_prefix}-proxy:{image_tag}",
    }

    for image in images.values():
        kind_cluster.load_docker_image(image)

    logging.info("Deploying openapi-collector ...")
    deployment_manifests_path = Path(__file__).parent / "deployment.yaml"

    with NamedTemporaryFile(mode="w+") as tmp:
        with deployment_manifests_path.open() as f:
            resources = list(yaml.safe_load_all(f))
        dep = resources[-1]
        assert (
            dep["kind"] == "Deployment"
            and dep["metadata"]["name"] == "openapi-collector"
        )

        for container in dep["spec"]["template"]["spec"]["containers"]:
            if container["name"] in images:
                container["image"] = images[container["name"]]

        yaml.dump_all(documents=resources, stream=tmp)

        kind_cluster.kubectl("apply", "-f", tmp.name)

    logging.info("Waiting for rollout ...")
    kind_cluster.kubectl("rollout", "status", "deployment/openapi-collector")

    return kind_cluster


@fixture(scope="session")
def collector_url(cluster):
    with cluster.port_forward("svc/openapi-collector", 80) as port:
        yield f"http://localhost:{port}/"


@fixture(scope="function")
def populated_cluster(cluster):
    try:
        test_resources_manifests_path = Path(__file__).parent / "test-resources.yaml"
        cluster.kubectl("apply", "-f", str(test_resources_manifests_path))
        cluster.kubectl("rollout", "status", "deployment/petstore")
        yield cluster
    
    finally:
        cluster.kubectl("delete", "-f", str(test_resources_manifests_path))


@fixture(scope="function")
def svc_resource(populated_cluster):
    name = "petstore"
    namespace = "default"
    api = populated_cluster.api
    svc = pykube.Service.objects(api).get(name=name, namespace=namespace)

    # wait some time for collection cycle
    time.sleep(10)

    yield {
        "obj": svc,
        "name": name,
        "namespace": namespace
    }
