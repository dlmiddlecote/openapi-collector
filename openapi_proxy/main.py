import logging

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
app.logger = logging.getLogger('openapi_proxy')


@app.route('/<path:base_path>/openapi.json', methods=['GET'])
def get_spec(base_path):
    new_host = request.headers.get('ServerHost')
    if not new_host:
        return jsonify({"msg": "missing ServerHost header"}), 400

    new_path = '/'.join(base_path.split('/')[1:])
    url = request.url.replace(request.host_url.strip("/"), new_host)

    if not new_path:
        base_path += '/'
    url = url.replace(base_path, new_path)

    try:
        resp = requests.get(
            url=url,
            headers={key: value for (key, value) in request.headers if key.lower() not in {'host', 'serverhost'}},
            cookies=request.cookies,
            allow_redirects=False)
        resp.raise_for_status()

    except Exception as e:
        app.logger.exception("Error getting spec: %s", e)
        return jsonify({"msg": "error"}), 500

    spec = resp.json()
    servers = spec.get("servers") or [{"url": "", "description": ""}]
    for server in servers:
        url = server.get("url", "")
        url = f"/{base_path.split('/')[0]}{url}"

        description = server.get("description", "")
        if description:
            description += " - "
        description += "Not real base path"

        server["url"] = url
        server["description"] = description

    spec['servers'] = servers

    return jsonify(spec), 200


@app.route('/healthz', methods=['GET'])
def healthz():
    return '', 200


def main():  # pragma: no cover
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        level=logging.INFO,
    )
    app.run(host='0.0.0.0', debug=False)
