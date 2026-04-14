SHELL := bash
REPOSITORY := https://repository.genesis-core.tech
ifeq ($(SSH_KEY),)
	SSH_KEY = ~/.ssh/id_rsa.pub
endif

all: help

help:
	@echo "build_core       - build genesis core"
	@echo "bootstrap        - bootstrap genesis core"

build_core:
	genesis build -i $(SSH_KEY) -f . --inventory --manifest-var repository=https://repository.genesis-core.tech

bootstrap:
	genesis bootstrap -i output/inventory.json -f -m core --admin-password admin --cidr 10.20.0.0/22
