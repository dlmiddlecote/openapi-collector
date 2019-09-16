import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

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

    with kind_cluster.port_forward("service/openapi-collector", 80) as port:
        url = f"http://localhost:{port}/"
        yield {"url": url}


@fixture(scope="session")
def populated_cluster(cluster):
    return cluster
