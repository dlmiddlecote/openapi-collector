import pytest

import os.path

from unittest.mock import MagicMock

from openapi_collector.main import main


@pytest.fixture
def kubeconfig(tmpdir):
    kubeconfig = tmpdir.join("kubeconfig")
    kubeconfig.write("""
apiVersion: v1
clusters:
- cluster: {server: "https://localhost:9443"}
  name: test
contexts:
- context: {cluster: test, user: test}
  name: test
current-context: test
kind: Config
preferences: {}
users:
- name: test
  user: {token: test}
    """)
    return kubeconfig


def test_main_continue_on_failure(kubeconfig, monkeypatch):
    monkeypatch.setattr(os.path, "expanduser", lambda x: str(kubeconfig))

    mock_shutdown = MagicMock()
    mock_handler = MagicMock()
    mock_handler.shutdown_now = False
    mock_shutdown.GracefulShutdown.return_value = mock_handler

    calls = []

    def mock_collect_specs(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            raise Exception("collect_specs fails on first run")
        elif len(calls) == 2:
            mock_handler.shutdown_now = True

    monkeypatch.setattr("openapi_collector.main.collect_specs", mock_collect_specs)
    monkeypatch.setattr("openapi_collector.main.shutdown", mock_shutdown)

    main(["--interval=0"])

    assert len(calls) == 2
