import json
import logging
import time

import pykube
import requests


def test_initial_config(cluster):
    api = cluster.api

    # Wait for some collection cycles to happen
    time.sleep(15)

    # Check initial ui configmap
    ui_cm = pykube.ConfigMap.objects(api).get(name="openapi-collector-ui-config")
    assert ui_cm, "UI ConfigMap not found"

    swagger_conf = json.loads(ui_cm.obj["data"]["swagger-config.json"])
    assert "urls" in swagger_conf
    assert [] == swagger_conf["urls"]

    # Check initial router configmap
    router_cm = pykube.ConfigMap.objects(api).get(
        name="openapi-collector-router-config"
    )
    assert router_cm, "Router ConfigMap not found"

    assert router_cm.obj.get("data") is None


def test_collects_service(populated_cluster, svc_resource, collector_url):
    api = populated_cluster.api

    name = svc_resource["name"]
    namespace = svc_resource["namespace"]

    logging.info("Getting ConfigMaps...")
    ui_cm = pykube.ConfigMap.objects(api).get(name="openapi-collector-ui-config")
    router_cm = pykube.ConfigMap.objects(api).get(
        name="openapi-collector-router-config"
    )

    # Check ui configmap has been updated correctly
    swagger_conf = json.loads(ui_cm.obj["data"]["swagger-config.json"])
    assert "urls" in swagger_conf
    assert 1 == len(swagger_conf["urls"])
    assert f"{namespace}/{name}" == swagger_conf["urls"][0]["name"]
    assert f"/{name}-{namespace}/api/openapi.json" == swagger_conf["urls"][0]["url"]

    # Check router configmap has been updated correctly
    assert f"{name}-{namespace}-upstream.conf" in router_cm.obj["data"]
    assert f"{name}-{namespace}-location.conf" in router_cm.obj["data"]

    # Wait for k8s to inject configmaps into containers
    logging.info("Waiting for ConfigMap injection ..")
    time.sleep(90)

    # Check config is exposed to be used by the ui
    swagger_conf = requests.get(f"{collector_url}/swagger-config.json").json()
    assert "urls" in swagger_conf
    assert 1 == len(swagger_conf["urls"])
    assert f"{namespace}/{name}" == swagger_conf["urls"][0]["name"]
    assert f"/{name}-{namespace}/api/openapi.json" == swagger_conf["urls"][0]["url"]

    # Check we can get to the exposed API
    logging.info("Requesting spec...")
    api_spec_path = f"/{name}-{namespace}/api/openapi.json"
    resp = requests.get(f"{collector_url}{api_spec_path}")
    resp.raise_for_status()

    assert resp.json()

    # Check base url has been updated
    for server in resp.json()["servers"]:
        assert server["url"].startswith(f"/{name}-{namespace}")

    # Make request via proxy
    resp = requests.get(f"{collector_url}/{name}-{namespace}/api/")
    resp.raise_for_status()

    assert "Hey" == resp.text
