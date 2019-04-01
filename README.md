# Kubernetes OpenAPI Spec Collector

[![Build Status](https://travis-ci.org/dlmiddlecote/openapi-collector.svg?branch=master)](https://travis-ci.org/dlmiddlecote/openapi-collector)
[![Coverage Status](https://coveralls.io/repos/github/dlmiddlecote/openapi-collector/badge.svg?branch=master)](https://coveralls.io/github/dlmiddlecote/openapi-collector?branch=master)

Kubernetes OpenAPI Spec Collector aggregates (collects) all specifications exposed by services inside a Kubernetes Cluster, into a single UI for quick exploration.

By processing annotated `Service`s, the UI is automatically updated with new specifications as they are added or evolve, and is an excellent way to explore APIs.

## Design

## Usage

Deploy the collector into your cluster:
```
$ kubectl apply -f deploy/
```

To see the collector in action, deploy an app that exposes an OpenAPI spec, and annotate the service that points to the app. 
```
$ # deploy app
$ kubectl annotate service app openapi/collect=true
$ kubectl annotate service app openapi/port=80  # port name or number that the spec is accessible at
$ kubectl annotate service app openapi/path=/. # base path of specification
```

You should be able to then connect to the collector Pod and see the specification in the UI. NOTE: This may take some time to appear, dependent on the poll interval of the collector, and also [the Kubelet sync period](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/#mounted-configmaps-are-updated-automatically).

## Configuration

The OpenAPI Spec Collector is configured via command line args and Kubernetes annotations.

*Kubernetes Annotations*

`openapi/collect`
	Annotate `Service` resource with value `”true”`  to mark the `Service` as one exposing an OpenAPI spec, and one that should be collected. 

`openapi/port`
	Annotate `Service` resource with the port number or name that the OpenAPI spec will be exposed at.

`openapi/path`
	Annotate `Service` resource with the base path of the OpenAPI spec, i.e. use the value `”/“` if the spec is available at `/openapi.json`.

*Command line args*

`—debug`
	Print more information.

`—interval`
	Loop interval (default 30s).

## Contributing

The best way to contribute is to provide feedback. I’d love to hear what you like and what could be better. PRs and Issues more than welcome!

## Local Development

You can run the collector against your current kubeconfig context like this:
```
$ pip install pipenv
$ pipenv install —dev
$ pipenv she’ll
$ python -m openapi_collector
```

To run tests:
```
$ make test
```

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see [http://www.gnu.org/licenses/](http://www.gnu.org/licenses/).
