FROM python:3.9-slim

WORKDIR /

RUN pip3 install poetry

COPY poetry.lock /
COPY pyproject.toml /

# fake package to make Poetry happy
RUN mkdir /openapi_proxy && touch /openapi_proxy/__init__.py && touch /README.md

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-dev --no-ansi

FROM python:3.9-slim

WORKDIR /

# copy pre-built packages to this image
COPY --from=0 /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

COPY openapi_proxy /openapi_proxy

ARG VERSION=dev
RUN sed -i "s/__version__ = .*/__version__ = '${VERSION}'/" /openapi_proxy/__init__.py

ENTRYPOINT ["python3", "-m", "openapi_proxy"]
