FROM python:3.7-alpine

WORKDIR /

COPY Pipfile.lock /
COPY pipenv-install.py /

RUN /pipenv-install.py && \
    rm -fr /usr/local/lib/python3.7/site-packages/pip && \
    rm -fr /usr/local/lib/python3.7/site-packages/setuptools

FROM python:3.7-alpine

WORKDIR /

COPY --from=0 /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
COPY openapi_proxy /openapi_proxy

ARG VERSION=dev
RUN sed -i "s/__version__ = .*/__version__ = '${VERSION}'/" /openapi_proxy/__init__.py

ENTRYPOINT ["python3", "-m", "openapi_proxy"]
