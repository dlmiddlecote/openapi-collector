import json
from unittest.mock import MagicMock

import pykube

from openapi_collector.collector import (
    collect_specs,
    should_collect,
    parse_port,
    parse_path,
)


def test_should_collect_true():
    svc = pykube.Service(
        None, {"metadata": {"annotations": {"openapi/collect": "true"}}}
    )
    assert should_collect(svc)


def test_should_collect_false():
    svc = pykube.Service(
        None, {"metadata": {"annotations": {"openapi/collect": "false"}}}
    )
    assert not should_collect(svc)


def test_should_collect_True():
    svc = pykube.Service(
        None, {"metadata": {"annotations": {"openapi/collect": "True"}}}
    )
    assert should_collect(svc)


def test_should_collect_missing():
    svc = pykube.Service(None, {"metadata": {"annotations": {}}})
    assert not should_collect(svc)


def test_parse_port_int():
    svc = pykube.Service(None, {"metadata": {"annotations": {"openapi/port": "8000"}}})
    assert 8000 == parse_port(svc)


def test_parse_port_default():
    svc = pykube.Service(None, {"metadata": {"annotations": {}}})
    assert 80 == parse_port(svc)


def test_parse_port_name():
    svc = pykube.Service(
        None,
        {
            "metadata": {"annotations": {"openapi/port": "api-port"}},
            "spec": {"ports": [{"name": "api-port", "port": "8000"}]},
        },
    )

    assert 8000 == parse_port(svc)


def test_parse_port_name_missing():
    svc = pykube.Service(
        None,
        {
            "metadata": {"annotations": {"openapi/port": "missing"}},
            "spec": {"ports": [{"name": "api-port", "port": "8000"}]},
        },
    )

    assert parse_port(svc) is None


def test_parse_path():
    svc = pykube.Service(None, {"metadata": {"annotations": {"openapi/path": "/v1"}}})
    assert "/v1" == parse_path(svc)


def test_parse_path_default():
    svc = pykube.Service(None, {"metadata": {"annotations": {}}})
    assert "/" == parse_path(svc)


def test_collect_specs_no_cms():
    api_mock = MagicMock(config=MagicMock(namespace="default"))

    def get(**kwargs):
        response = MagicMock()

        if kwargs.get("url") == "services":
            data = {
                "items": [
                    {
                        "metadata": {
                            "name": "svc-1",
                            "namespace": "ns-1",
                            "annotations": {"openapi/collect": "true"},
                        }
                    }
                ]
            }

        elif kwargs.get("url") == "/configmaps/openapi-collector-router-config":
            data = {}
            response.status_code = 404
            response.ok = False

        elif kwargs.get("url") == "/configmaps/openapi-collector-ui-config":
            data = {}
            response.status_code = 404
            response.ok = False

        else:
            data = {}

        response.json.return_value = data
        return response

    api_mock.get = get

    collect_specs(api_mock)

    assert 2 == api_mock.post.call_count
    assert not api_mock.delete.called

    _, nginx_call = api_mock.post.call_args_list[0]
    assert "configmaps" == nginx_call["url"]
    nginx_data = json.loads(nginx_call["data"])
    assert "openapi-collector-router-config" == nginx_data["metadata"]["name"]
    assert "svc-1-ns-1-location.conf" in nginx_data["data"]
    assert "svc-1-ns-1-upstream.conf" in nginx_data["data"]

    _, swagger_call = api_mock.post.call_args_list[1]
    assert "configmaps" == swagger_call["url"]
    swagger_data = json.loads(swagger_call["data"])
    assert "openapi-collector-ui-config" == swagger_data["metadata"]["name"]
    assert "swagger-config.json" in swagger_data["data"]


def test_collect_specs_cm_replaced():
    api_mock = MagicMock(config=MagicMock(namespace="default"))

    def get(**kwargs):
        response = MagicMock()

        if kwargs.get("url") == "services":
            data = {
                "items": [
                    {
                        "metadata": {
                            "name": "svc-1",
                            "namespace": "ns-1",
                            "annotations": {"openapi/collect": "true"},
                        }
                    }
                ]
            }

        elif kwargs.get("url") == "/configmaps/openapi-collector-router-config":
            data = {
                "items": [
                    {
                        "metadata": {"name": "openapi-collector-router-config"},
                        "data": {"foo.conf": ""},
                    }
                ]
            }

        elif kwargs.get("url") == "/configmaps/openapi-collector-ui-config":
            data = {
                "items": [
                    {
                        "metadata": {"name": "openapi-collector-ui-config"},
                        "data": {
                            "swagger-config.json": """{
                            "urls": [{"name": "foo", "url": "/foo}]
                        }"""
                        },
                    }
                ]
            }

        else:
            data = {}

        response.json.return_value = data
        return response

    api_mock.get = get

    collect_specs(api_mock)

    assert 2 == api_mock.post.call_count
    assert 2 == api_mock.delete.call_count

    _, nginx_call = api_mock.post.call_args_list[0]
    assert "configmaps" == nginx_call["url"]
    nginx_data = json.loads(nginx_call["data"])
    assert "openapi-collector-router-config" == nginx_data["metadata"]["name"]
    assert "svc-1-ns-1-location.conf" in nginx_data["data"]
    assert "svc-1-ns-1-upstream.conf" in nginx_data["data"]
    assert "foo.conf" not in nginx_data["data"]

    _, swagger_call = api_mock.post.call_args_list[1]
    assert "configmaps" == swagger_call["url"]
    swagger_data = json.loads(swagger_call["data"])
    assert "openapi-collector-ui-config" == swagger_data["metadata"]["name"]
    assert "swagger-config.json" in swagger_data["data"]
    swagger_conf = json.loads(swagger_data["data"]["swagger-config.json"])
    assert "foo" not in set(u["name"] for u in swagger_conf["urls"])

    _, nginx_delete_call = api_mock.delete.call_args_list[0]
    assert "/configmaps/openapi-collector-router-config" == nginx_delete_call["url"]

    _, swagger_delete_call = api_mock.delete.call_args_list[1]
    assert "/configmaps/openapi-collector-ui-config" == swagger_delete_call["url"]


def test_collect_specs_no_services():
    api_mock = MagicMock(config=MagicMock(namespace="default"))

    def get(**kwargs):
        response = MagicMock()

        if kwargs.get("url") == "services":
            data = {
                "items": [
                    {
                        "metadata": {
                            "name": "svc-1",
                            "namespace": "ns-1",
                            "annotations": {"openapi/collect": "false"},
                        }
                    }
                ]
            }

        elif kwargs.get("url") == "/configmaps/openapi-collector-router-config":
            data = {}
            response.status_code = 404
            response.ok = False

        elif kwargs.get("url") == "/configmaps/openapi-collector-ui-config":
            data = {}
            response.status_code = 404
            response.ok = False

        else:
            data = {}

        response.json.return_value = data
        return response

    api_mock.get = get

    collect_specs(api_mock)

    assert 2 == api_mock.post.call_count
    assert not api_mock.delete.called

    _, nginx_call = api_mock.post.call_args_list[0]
    assert "configmaps" == nginx_call["url"]
    nginx_data = json.loads(nginx_call["data"])
    assert "openapi-collector-router-config" == nginx_data["metadata"]["name"]
    assert not nginx_data["data"]

    _, swagger_call = api_mock.post.call_args_list[1]
    assert "configmaps" == swagger_call["url"]
    swagger_data = json.loads(swagger_call["data"])
    assert "openapi-collector-ui-config" == swagger_data["metadata"]["name"]
    assert "swagger-config.json" in swagger_data["data"]
    swagger_conf = json.loads(swagger_data["data"]["swagger-config.json"])
    assert not swagger_conf["urls"]


def test_collect_specs_skip_no_port():
    api_mock = MagicMock(config=MagicMock(namespace="default"))

    def get(**kwargs):
        response = MagicMock()

        if kwargs.get("url") == "services":
            data = {
                "items": [
                    {
                        "metadata": {
                            "name": "svc-1",
                            "namespace": "ns-1",
                            "annotations": {
                                "openapi/collect": "true",
                                "openapi/port": "missing",
                            },
                        },
                        "spec": {"ports": []},
                    },
                    {
                        "metadata": {
                            "name": "svc-2",
                            "namespace": "ns-1",
                            "annotations": {"openapi/collect": "true"},
                        }
                    },
                ]
            }

        elif kwargs.get("url") == "/configmaps/openapi-collector-router-config":
            data = {}
            response.status_code = 404
            response.ok = False

        elif kwargs.get("url") == "/configmaps/openapi-collector-ui-config":
            data = {}
            response.status_code = 404
            response.ok = False

        else:
            data = {}

        response.json.return_value = data
        return response

    api_mock.get = get

    collect_specs(api_mock)

    assert 2 == api_mock.post.call_count
    assert not api_mock.delete.called

    _, nginx_call = api_mock.post.call_args_list[0]
    assert "configmaps" == nginx_call["url"]
    nginx_data = json.loads(nginx_call["data"])
    assert "openapi-collector-router-config" == nginx_data["metadata"]["name"]
    assert "svc-1-ns-1-location.conf" not in nginx_data["data"]
    assert "svc-1-ns-1-upstream.conf" not in nginx_data["data"]

    _, swagger_call = api_mock.post.call_args_list[1]
    assert "configmaps" == swagger_call["url"]
    swagger_data = json.loads(swagger_call["data"])
    assert "openapi-collector-ui-config" == swagger_data["metadata"]["name"]
    assert "swagger-config.json" in swagger_data["data"]
    swagger_conf = json.loads(swagger_data["data"]["swagger-config.json"])
    assert 1 == len(swagger_conf["urls"])
