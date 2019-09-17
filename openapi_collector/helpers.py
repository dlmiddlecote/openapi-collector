import os

import pykube


def get_kube_api():
    try:
        config = pykube.KubeConfig.from_service_account()
    except FileNotFoundError:
        # local testing
        config = pykube.KubeConfig.from_file(os.getenv("KUBECONFIG", "~/.kube/config"))

    api = pykube.HTTPClient(config)
    return api
