.PHONY: test docker push

IMAGE_PREFIX ?= dlmiddlecote/openapi
VERSION      ?= $(shell git describe --tags --always --dirty)
TAG          ?= $(VERSION)

CLUSTER_NAME ?= kind

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
	docker push "$(IMAGE_PREFIX)-router:$(TAG)"
	docker push "$(IMAGE_PREFIX)-collector:$(TAG)"
	docker push "$(IMAGE_PREFIX)-proxy:$(TAG)"

create-kind:
	kind create cluster  --name $(CLUSTER_NAME)

delete-kind:
	kind delete cluster  --name $(CLUSTER_NAME)

load:
	kind load docker-image $(IMAGE_PREFIX)-router:$(TAG) --name $(CLUSTER_NAME)
	kind load docker-image $(IMAGE_PREFIX)-collector:$(TAG) --name $(CLUSTER_NAME)
	kind load docker-image $(IMAGE_PREFIX)-proxy:$(TAG) --name $(CLUSTER_NAME)

update-deploy-files:
	perl -i -pe"s/image: $(subst /,\/,$(IMAGE_PREFIX))-(.*):.*/image: $(subst /,\/,$(IMAGE_PREFIX))-\1:$(subst /,\/,$(TAG))/g" ./deploy/deployment.yaml

integration-tests: create-kind load update-deploy-files
	CLUSTER_NAME=$(CLUSTER_NAME) VERSION=$(VERSION) ./scripts/integration-tests
	make delete-kind CLUSTER_NAME=$(CLUSTER_NAME)