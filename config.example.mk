D := docker
DOCKER_DIR := ./docker
DOCKER_IMAGE_VER := 0.1
DOCKER_IMAGE_NAME := asyncjob
DOCKER_IMAGE := $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_VER)
USER_ID := $(shell id -u)
GROUP_ID := $(shell id -g)

# Template of the wheel distribution file.
# $${ver} should be in place where the real version should be placed.
DIST_FILE_TMPL := asyncjob-$${ver}-py3-none-any.whl
