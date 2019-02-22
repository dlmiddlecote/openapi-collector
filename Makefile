.PHONY: test docker push

IMAGE_PREFIX ?= dlmiddlecote/openapi
VERSION      ?= $(shell git describe --tags --always --dirty)
TAG          ?= $(VERSION)

default: docker

test:
	pipenv run flake8
	pipenv run coverage run --source openapi_collector -m py.test tests/collector
	pipenv run coverage run -a --source openapi_proxy -m py.test tests/proxy
	pipenv run coverage report
 
docker:
	docker build --build-arg "VERSION=$(VERSION)" -t "$(IMAGE_PREFIX)-router:$(TAG)" -f ./docker/router/Dockerfile .
	docker build --build-arg "VERSION=$(VERSION)" -t "$(IMAGE_PREFIX)-collector:$(TAG)" -f ./docker/collector/Dockerfile .
	docker build --build-arg "VERSION=$(VERSION)" -t "$(IMAGE_PREFIX)-proxy:$(TAG)" -f ./docker/proxy/Dockerfile .
	@echo 'Docker images $(IMAGE_PREFIX)-router:$(TAG), $(IMAGE_PREFIX)-collector:$(TAG), $(IMAGE_PREFIX)-proxy:$(TAG) can now be used.'

push: docker
	docker push t "$(IMAGE_PREFIX)-router:$(TAG)"
	docker push t "$(IMAGE_PREFIX)-collector:$(TAG)"
	docker push t "$(IMAGE_PREFIX)-proxy:$(TAG)"
