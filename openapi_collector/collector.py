import logging
from collections import namedtuple

import pykube

from openapi_collector.config_gen import build_nginx_configmap, build_swagger_configmap

logger = logging.getLogger(__name__)


COLLECT_ANNOTATION = "openapi/collect"
PATH_ANNOTATION = "openapi/path"
PORT_ANNOTATION = "openapi/port"


Spec = namedtuple('Spec', ['name', 'namespace', 'port', 'path'])


def should_collect(svc):
    return svc.annotations.get(COLLECT_ANNOTATION, "false").lower() == "true"


def parse_port(svc):
    port_value = svc.annotations.get(PORT_ANNOTATION, "80")

    try:
        port = int(port_value)

    except ValueError:
        for port_spec in svc.obj["spec"]["ports"]:
            if port_spec["name"] == port_value:
                port = int(port_spec["port"])
                break
        else:
            port = None

    return port


def parse_path(svc):
    return svc.annotations.get(PATH_ANNOTATION, "/")


def collect_specs(api):
    specs = []
    for svc in pykube.Service.objects(api, namespace=pykube.all):
        if should_collect(svc):
            logger.info(f'Collecting {svc.namespace}/{svc.name}')

            path = parse_path(svc)
            port = parse_port(svc)
            if port is None:
                logger.warning(f"Cannot parse port for service {svc.namespace}/{svc.name}")
                continue

            specs.append(Spec(svc.name, svc.namespace, port, path))

    nginx_cm = build_nginx_configmap(api, specs)
    swagger_cm = build_swagger_configmap(api, specs)

    for cm in [nginx_cm, swagger_cm]:
        if cm.exists():
            cm.delete()
        cm.create()
