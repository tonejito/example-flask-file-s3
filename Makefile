#!/usr/bin/make -f
# Makefile for the Flask image tool

SHELL=/bin/bash
FLASK_APP=app.py
FLASK_ENV?=development
HOST?=localhost
NAME=image-tool
IMAGE_TAG?=${NAME}:latest
IMAGE_REGISTRIES?=docker.io/tonejito quay.io/tonejito
HOST_PORT?=5000
CONTAINER_PORT?=5000
UPLOAD_FOLDER?=/tmp/storage
ENV_FILE=.env

# ephemeral pvc s3 s3-obc
TYPE?=pvc

SCC?=
SCC_LIST=anyuid hostaccess hostmount-anyuid hostnetwork nonroot privileged restricted

default:	run

podman:	podman-build podman-run
podman-all: podman-build podman-tag podman-push

podman-build:	Containerfile
	podman build -t ${IMAGE_TAG} .

podman-run:
ifeq (,$(wildcard ${ENV_FILE}))
	podman run -it -p ${HOST_PORT}:${CONTAINER_PORT} ${IMAGE_TAG}
else
	podman run -it --env-file ${ENV_FILE} -p ${HOST_PORT}:${CONTAINER_PORT} ${IMAGE_TAG}
endif

podman-tag:
	for REGISTRY in ${IMAGE_REGISTRIES} ; \
	do \
	  echo $${REGISTRY}/${IMAGE_TAG} ; \
	  podman tag localhost/${IMAGE_TAG} $${REGISTRY}/${IMAGE_TAG} ; \
	done ;

podman-push:
	for REGISTRY in ${IMAGE_REGISTRIES} ; \
	do \
	  echo $${REGISTRY}/${IMAGE_TAG} ; \
	  podman push $${REGISTRY}/${IMAGE_TAG} ; \
	done ;

install:	requirements.txt
	pip3 install --user --requirement requirements.txt

run:	${FLASK_APP}
	mkdir -vp ${UPLOAD_FOLDER}
	test -e ${ENV_FILE}.sh && source ${ENV_FILE}.sh || true && \
	FLASK_ENV=${FLASK_ENV} FLASK_APP=${FLASK_APP} UPLOAD_FOLDER=${UPLOAD_FOLDER} \
	flask $@ --host=${HOST} --port=${HOST_PORT}

wsgi:	${FLASK_APP}
	mkdir -vp ${UPLOAD_FOLDER}
	test -e ${ENV_FILE}.sh && source ${ENV_FILE}.sh || true && \
	gunicorn app:app --bind ${HOST}:${HOST_PORT} --reload --preload --capture-output --log-level info --access-logfile - --error-logfile -

oc-test:	oc-create oc-delete
	$(MAKE) oc-create
	oc get pods -w
	$(MAKE) oc-delete

oc-reset:	oc-delete oc-create

deploy:	oc-create
oc-create:
	oc new-project ${NAME}
	oc kustomize kustomization/overlays/${TYPE}/ | oc apply -f -
ifneq (,${SCC})
	$(MAKE) scc-grant
endif
	oc get all

clean:	oc-delete
oc-delete:
	oc kustomize kustomization/overlays/${TYPE}/ | oc delete -f - || true
ifneq (,${SCC})
	$(MAKE) scc-revoke
endif
	oc project default
	oc delete project/${NAME}
	oc get project/${NAME} -w

scc-grant:
	echo ${SCC_LIST} | tr ' ' '\n' | xargs -r -t -n 1 -I {} -n 1 ${SHELL} -c "oc adm policy add-scc-to-user {} -z ${NAME} || true"
	echo 0 1 | xargs -r -t -n 1 oc scale deployment/${NAME}-${TYPE} --replicas

scc-revoke:
	echo ${SCC_LIST} | tr ' ' '\n' | xargs -r -t -n 1 -I {} -n 1 ${SHELL} -c "oc adm policy remove-scc-from-user {} -z ${NAME} || true"

oc-logs:
	oc logs deployment/${NAME}-${TYPE} -f

oc-debug:
	# oc debug deployment/${NAME}
	oc exec -it $(shell oc get pods -l app=${NAME} -o jsonpath='{.items[0].metadata.name}') /bin/sh

again:
	reset
	$(MAKE) podman-all oc-reset oc-logs
