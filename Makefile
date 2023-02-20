include ./config.mk

PACKAGE_NAME := asyncjob
CONTAINER_CMD := $(D) run --rm -ti -w /opt/$(PACKAGE_NAME) -v $$(pwd):/opt/$(PACKAGE_NAME) $(DOCKER_IMAGE)

DEPS := $(DOCKER_DIR)/Dockerfile \
		$(DOCKER_DIR)/requirements.txt \
		$(DOCKER_DIR)/requirements-dev.txt \

.PHONY: init
init: ./config.mk
	@echo -e "You can use the config.mk file to customize it for your needs before going any further."

.PHONY: build-img
build-img: .docker-beacon

.PHONY: dist
dist: check
	@$(CONTAINER_CMD) python setup.py bdist_wheel

.PHONY: check
check: .docker-beacon
	@$(CONTAINER_CMD) \
		/bin/sh -c "python -m black --check $(PACKAGE_NAME) && \
					python -m flake8 $(PACKAGE_NAME) && \
					python -m isort -c $(PACKAGE_NAME) && \
					python -m mypy --strict $(PACKAGE_NAME)"

.PHONY: fix-style
fix-style: .docker-beacon
	@$(CONTAINER_CMD) \
		/bin/sh -c "python -m isort $(PACKAGE_NAME) && python -m black $(PACKAGE_NAME)"

.docker-beacon: $(DEPS)
	@$(D) build -t $(DOCKER_IMAGE) \
		--build-arg USER_ID=$(USER_ID) \
		--build-arg GROUP_ID=$(GROUP_ID) \
		$(DOCKER_DIR) && touch $@

$(DOCKER_DIR)/requirements.txt: ./requirements.txt
	@cp $< $@

$(DOCKER_DIR)/requirements-dev.txt: ./requirements-dev.txt
	@cp $< $@

./config.mk: ./config.example.mk
	@cp $< $@
