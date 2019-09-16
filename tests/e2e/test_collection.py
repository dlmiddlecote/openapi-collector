import json
import time

import pykube
import requests


def test_initial_config(cluster):
    api = cluster.api

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

    ui_cm = pykube.ConfigMap.objects(api).get(name="openapi-collector-ui-config")
    router_cm = pykube.ConfigMap.objects(api).get(
        name="openapi-collector-router-config"
    )

    # Check ui configmap has been updated correctly
    swagger_conf = json.loads(ui_cm.obj["data"]["swagger-config.json"])
    assert "urls" in swagger_conf
    assert 1 == len(swagger_conf["urls"])
    assert f"{namespace}/{name}" == swagger_conf["urls"][0]["name"]
    assert f"/{name}-{namespace}/api/swagger.json" == swagger_conf["urls"][0]["url"]

    # Check router configmap has been updated correctly
    assert f"{name}-{namespace}-upstream.conf" in router_cm.obj["data"]
    assert f"{name}-{namespace}-location.conf" in router_cm.obj["data"]

    # Wait for k8s to inject configmaps into containers
    time.sleep(60)

    # Check config is exposed
    swagger_conf = requests.get(
        f"{collector_url.rstrip('/')}/swagger-config.json"
    ).json()
    assert "urls" in swagger_conf
    assert 1 == len(swagger_conf["urls"])
    assert f"{namespace}/{name}" == swagger_conf["urls"][0]["name"]
    assert f"/{name}-{namespace}/api/swagger.json" == swagger_conf["urls"][0]["url"]
