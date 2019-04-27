import json

import pykube


ROUTER_CONFIGMAP_NAME = 'openapi-collector-router-config'
UI_CONFIGMAP_NAME = 'openapi-collector-ui-config'

NGINX_UPSTREAM_TMPL = """
upstream {host} {{
  server {name}.{namespace}:{port};
}}
"""
NGINX_LOCATION_TMPL = """
location = /{host}/{spec_path} {{
  proxy_set_header ServerHost "http://{name}.{namespace}:{port}";
  proxy_pass       http://proxy;
}}

location /{host} {{
  rewrite          /{host}/(.*) /$1 break;
  proxy_pass       http://{host};
}}
"""


def urljoin(*args):
    """
    Joins given arguments into a url. Trailing and leading slashes are
    stripped from each argument, before being joined
    """
    return "/".join(filter(bool, map(lambda x: str(x).strip("/"), args)))


def get_spec_path(spec):
    return urljoin(spec.path, "openapi.json")


def build_router_configmap(api, specs):
    cm_spec = {
        "metadata": {
            "name": ROUTER_CONFIGMAP_NAME,
        },
    }

    cm_data = {}

    for spec in specs:
        host = f"{spec.name}-{spec.namespace}"
        upstream_filename = f"{host}-upstream.conf"
        location_filename = f"{host}-location.conf"

        spec_path = get_spec_path(spec)

        cm_data[upstream_filename] = NGINX_UPSTREAM_TMPL.format(
            host=host,
            name=spec.name,
            namespace=spec.namespace,
            port=spec.port,
        )
        cm_data[location_filename] = NGINX_LOCATION_TMPL.format(
            host=host,
            name=spec.name,
            namespace=spec.namespace,
            port=spec.port,
            spec_path=spec_path,
        )

    cm_spec["data"] = cm_data

    return pykube.ConfigMap(api, cm_spec)


def build_ui_configmap(api, specs):
    cm_spec = {
        "metadata": {
            "name": UI_CONFIGMAP_NAME,
        },
    }

    urls = []
    for spec in specs:
        host = f"{spec.name}-{spec.namespace}"
        urls.append({
            "name": f"{spec.namespace}/{spec.name}",
            "url": f"/{urljoin(host, get_spec_path(spec))}"
        })

    cm_spec["data"] = {"swagger-config.json": json.dumps({"urls": urls})}

    return pykube.ConfigMap(api, cm_spec)
