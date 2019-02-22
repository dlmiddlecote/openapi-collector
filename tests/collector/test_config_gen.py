import json
from unittest.mock import MagicMock

import pykube

from openapi_collector.collector import Spec
from openapi_collector.config_gen import (
    NGINX_CONFIGMAP_NAME,
    SWAGGER_UI_CONFIGMAP_NAME,
    build_nginx_configmap,
    build_swagger_configmap,
)


def test_build_nginx_configmap():
    namespace = "default"
    # name, namespace, port, path
    spec = Spec("test-svc", "test-ns", 8000, "/v1")

    api_mock = MagicMock(config=MagicMock(namespace=namespace))

    cm = build_nginx_configmap(api_mock, [spec])

    assert type(cm) == pykube.ConfigMap
    assert namespace == cm.namespace
    assert NGINX_CONFIGMAP_NAME == cm.name
    assert "data" in cm.obj

    assert "test-svc-test-ns-upstream.conf" in cm.obj["data"]
    assert "test-svc-test-ns-location.conf" in cm.obj["data"]

    assert """
upstream test-svc-test-ns {
  server test-svc.test-ns:8000;
}
""" == cm.obj["data"]["test-svc-test-ns-upstream.conf"]

    assert """
location = /test-svc-test-ns/v1/openapi.json {
  proxy_set_header ServerHost "http://test-svc.test-ns:8000";
  proxy_pass       http://proxy;
}

location /test-svc-test-ns {
  rewrite          /test-svc-test-ns/(.*) /$1 break;
  proxy_pass       http://test-svc-test-ns;
}
""" == cm.obj["data"]["test-svc-test-ns-location.conf"]


def test_build_swagger_configmap():
    namespace = "default"
    # name, namespace, port, path
    spec = Spec("test-svc", "test-ns", 8000, "/v1")

    api_mock = MagicMock(config=MagicMock(namespace=namespace))

    cm = build_swagger_configmap(api_mock, [spec])

    assert type(cm) == pykube.ConfigMap
    assert namespace == cm.namespace
    assert SWAGGER_UI_CONFIGMAP_NAME == cm.name
    assert "data" in cm.obj

    assert "swagger-config.json" in cm.obj["data"]
    assert json.loads(cm.obj["data"]["swagger-config.json"])
    swagger_conf = json.loads(cm.obj["data"]["swagger-config.json"])
    assert "urls" in swagger_conf
    assert 1 == len(swagger_conf["urls"])
    assert "name" in swagger_conf["urls"][0]
    assert "url" in swagger_conf["urls"][0]
    assert "test-ns/test-svc" == swagger_conf["urls"][0]["name"]
    assert "/test-svc-test-ns/v1" == swagger_conf["urls"][0]["url"]
