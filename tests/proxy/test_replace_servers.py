from unittest.mock import MagicMock

import pytest
import requests

from openapi_proxy.main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.app_context():
        yield app.test_client()


def test_healthz_200(client):
    resp = client.get("/healthz")
    assert 200 == resp.status_code


def test_replace_servers_ok(client, monkeypatch):
    mock_requests = MagicMock()

    calls = []

    def get(**kwargs):
        calls.append(kwargs)

        response = MagicMock()
        response.json.return_value = {}
        return response

    mock_requests.get = get
    monkeypatch.setattr("openapi_proxy.main.requests", mock_requests)

    resp = client.get("/svc-ns/openapi.json", headers={"ServerHost": "svc.ns"})

    assert 1 == len(calls)
    assert "svc.ns/openapi.json" == calls[0]["url"]
    assert "host" not in {h.lower() for h in calls[0]["headers"]}
    assert "serverhost" not in {h.lower() for h in calls[0]["headers"]}

    assert "servers" in resp.json
    assert {"url": "/svc-ns", "description": "Not real base path"} == resp.json[
        "servers"
    ][0]


def test_replace_servers_append_base_to_existing(client, monkeypatch):
    mock_requests = MagicMock()

    calls = []

    def get(**kwargs):
        calls.append(kwargs)

        response = MagicMock()
        response.json.return_value = {"servers": [{"url": "/v1", "description": "foo"}]}
        return response

    mock_requests.get = get
    monkeypatch.setattr("openapi_proxy.main.requests", mock_requests)

    resp = client.get("/svc-ns/openapi.json", headers={"ServerHost": "svc.ns"})

    assert 1 == len(calls)
    assert "svc.ns/openapi.json" == calls[0]["url"]
    assert "host" not in {h.lower() for h in calls[0]["headers"]}
    assert "serverhost" not in {h.lower() for h in calls[0]["headers"]}

    assert "servers" in resp.json
    assert {
        "url": "/svc-ns/v1",
        "description": "foo - Not real base path",
    } == resp.json["servers"][0]


def test_replace_servers_keep_extra_base_path(client, monkeypatch):
    mock_requests = MagicMock()

    calls = []

    def get(**kwargs):
        calls.append(kwargs)

        response = MagicMock()
        response.json.return_value = {}
        return response

    mock_requests.get = get
    monkeypatch.setattr("openapi_proxy.main.requests", mock_requests)

    client.get("/svc-ns/v1/openapi.json", headers={"ServerHost": "svc.ns"})

    assert 1 == len(calls)
    assert "svc.ns/v1/openapi.json" == calls[0]["url"]


def test_replace_servers_missing_server_host(client):
    resp = client.get("/svc-ns/openapi.json")
    assert 400 == resp.status_code
    assert {"msg": "missing ServerHost header"} == resp.json


def test_replace_servers_request_error(client, monkeypatch):
    mock_requests = MagicMock()

    calls = []

    def get(**kwargs):
        calls.append(kwargs)

        response = MagicMock()
        response.status_code = 404
        response.json.return_value = {}
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error", response=response
        )
        return response

    mock_requests.get = get
    monkeypatch.setattr("openapi_proxy.main.requests", mock_requests)

    resp = client.get("/svc-ns/v1/openapi.json", headers={"ServerHost": "svc.ns"})

    assert 500 == resp.status_code
