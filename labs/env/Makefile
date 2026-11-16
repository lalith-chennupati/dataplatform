# SIM lab environment. Run from labs/env.
PROFILES ?= core
COMPOSE = docker compose $(foreach p,$(PROFILES),--profile $(p))

.PHONY: up up-all down destroy ps smoke kind-up kind-down

.env:
	cp .env.example .env

up: .env            ## start the core engines (S3, Iceberg REST, Trino, Postgres, Elasticsearch)
	$(COMPOSE) up -d

up-all: .env        ## start everything (core + spark + ai + infra + obs)
	$(MAKE) up PROFILES="core spark ai infra obs"

ps:
	docker compose --profile core --profile spark --profile ai --profile infra --profile obs ps

down:               ## stop containers, keep data
	docker compose --profile core --profile spark --profile ai --profile infra --profile obs down

destroy:            ## stop containers and delete all lab data volumes
	docker compose --profile core --profile spark --profile ai --profile infra --profile obs down -v

smoke:              ## run the smoke test against whatever is running
	./smoke-test.sh

kind-up:            ## 3-node kind cluster for the Kubernetes labs
	kind get clusters | grep -q aifactory-lab || kind create cluster --config kind/kind-config.yaml

kind-down:
	kind delete cluster --name aifactory-lab
