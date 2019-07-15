import logging
from collections import namedtuple

import pykube

from openapi_collector.config_gen import build_router_configmap, build_ui_configmap

logger = logging.getLogger(__name__)


COLLECT_ANNOTATION = "openapi/collect"
PATH_ANNOTATION = "openapi/path"
PORT_ANNOTATION = "openapi/port"


Spec = namedtuple('Spec', ['name', 'namespace', 'port', 'path'])


def should_collect(meta):
    return meta['annotations'].get(COLLECT_ANNOTATION, "false").lower() == "true"


def parse_port(meta, spec):
    port_value = meta['annotations'].get(PORT_ANNOTATION, "80")

    try:
        port = int(port_value)

    except ValueError:
        for port_spec in spec["ports"]:
            if port_spec["name"] == port_value:
                port = int(port_spec["port"])
                break
        else:
            port = None

    return port


def parse_path(meta):
    return meta['annotations'].get(PATH_ANNOTATION, "/")


# def collect_specs(api):
#     specs = []
#     for svc in pykube.Service.objects(api, namespace=pykube.all):
#         if should_collect(svc):
#             logger.info(f'Collecting {svc.namespace}/{svc.name}')

#             path = parse_path(svc)
#             port = parse_port(svc)
#             if port is None:
#                 logger.warning(f"Cannot parse port for service {svc.namespace}/{svc.name}")
#                 continue

#             specs.append(Spec(svc.name, svc.namespace, port, path))

#     router_cm = build_router_configmap(api, specs)
#     ui_cm = build_ui_configmap(api, specs)

#     for cm in [router_cm, ui_cm]:
#         if cm.exists():
#             cm.delete()
#         cm.create()

def remove_spec(specs, namespace, name):
    if namespace not in specs:
        return

    names = specs[namespace]

    if name not in names:
        return
    
    names.pop(name)

    if not names:
        specs.pop(namespace)

    return


async def remove_service(namespace, name, logger):
    async with CM_LOCK:
        remove_spec(SPECS, namespace, name)
        update_config_maps(SPECS)


async def collect_service(namespace, name, meta, spec, logger):
    path = parse_path(meta)
    port = parse_port(meta, spec)
    if port is None:
        logger.warning(f"OpenAPI Collector: Cannot parse port for service {namespace}/{name}")
        return

    logger.info(f'OpenAPI Collector: Collecting spec for {namespace}/{name}')

    async with CM_LOCK:
        SPECS.setdefault(namespace, {})[name] = Spec(name, namespace, port, path)
        update_config_maps(SPECS)


def update_config_maps(specs):
    api = get_kube_api()
    specs = [spec for names in specs.values() for spec in names.values()]
    router_cm = build_router_configmap(api, specs)
    ui_cm = build_ui_configmap(api, specs)

    for cm in [router_cm, ui_cm]:
        if cm.exists():
            cm.delete()
        cm.create()


import asyncio

import kopf

from openapi_collector.helpers import get_kube_api


SPECS = {}

CM_LOCK = asyncio.Lock()


@kopf.on.create('', 'v1', 'services')
async def start_service_collection(spec, meta, namespace, name, logger, **_):
    if should_collect(meta):
        await collect_service(namespace, name, meta, spec, logger)


@kopf.on.update('', 'v1', 'services')
@kopf.on.resume('', 'v1', 'services')
async def update_service_collection(namespace, name, meta, spec, logger, **_):
    if should_collect(meta):
        await collect_service(namespace, name, meta, spec, logger)
    else:
        await remove_service(namespace, name, logger)


@kopf.on.delete('', 'v1', 'services')
async def stop_service_collection(namespace, name, logger, **_):
    await remove_service(namespace, name, logger)