.PHONY: test docker push

IMAGE_PREFIX ?= dlmiddlecote/openapi
GITDIFFHASH       = $(shell git diff | md5sum | cut -c 1-4)
VERSION      ?= $(shell git describe --tags --always --dirty=-dirty-$(GITDIFFHASH))
TAG          ?= $(VERSION)
CLUSTER_NAME ?= kind

default: docker

.PHONY: test
test: poetry lint test.unit

.PHONY: poetry
poetry:
	poetry install

.PHONY: lint
lint:
	poetry run flake8
	poetry run black --check openapi_collector --check openapi_proxy

.PHONY: test.unit
test.unit:
	poetry run coverage run --source openapi_collector -m py.test tests/collector
	poetry run coverage run -a --source openapi_proxy -m py.test tests/proxy
	poetry run coverage report
 
.PHONY: test.e2e
test.e2e: docker
	env IMAGE_PREFIX=$(IMAGE_PREFIX) TAG=$(TAG) \
			poetry run pytest -v -r=a \
			       --log-cli-level info \
				   --log-cli-format '%(asctime)s %(levelname)s %(message)s' \
				   --cluster-name $(CLUSTER_NAME) \
				   tests/e2e

docker:
	docker build --build-arg "VERSION=$(VERSION)" -t "$(IMAGE_PREFIX)-router:$(TAG)" -f ./docker/router/Dockerfile .
	docker build --build-arg "VERSION=$(VERSION)" -t "$(IMAGE_PREFIX)-collector:$(TAG)" -f ./docker/collector/Dockerfile .
	docker build --build-arg "VERSION=$(VERSION)" -t "$(IMAGE_PREFIX)-proxy:$(TAG)" -f ./docker/proxy/Dockerfile .
	@echo 'Docker images $(IMAGE_PREFIX)-router:$(TAG), $(IMAGE_PREFIX)-collector:$(TAG), $(IMAGE_PREFIX)-proxy:$(TAG) can now be used.'

push: docker
	docker push "$(IMAGE_PREFIX)-router:$(TAG)"
	docker push "$(IMAGE_PREFIX)-collector:$(TAG)"
	docker push "$(IMAGE_PREFIX)-proxy:$(TAG)"

update-deploy-files:
	perl -i -pe"s/image: $(subst /,\/,$(IMAGE_PREFIX))-(.*):.*/image: $(subst /,\/,$(IMAGE_PREFIX))-\1:$(subst /,\/,$(TAG))/g" ./deploy/deployment.yaml

kind-load:
	kind load docker-image $(IMAGE_PREFIX)-router:$(TAG) --name $(CLUSTER_NAME)
	kind load docker-image $(IMAGE_PREFIX)-collector:$(TAG) --name $(CLUSTER_NAME)
	kind load docker-image $(IMAGE_PREFIX)-proxy:$(TAG) --name $(CLUSTER_NAME)
