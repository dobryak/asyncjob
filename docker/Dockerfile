FROM python:3.10-alpine

ARG USER_ID=1000
ARG GROUP_ID=1000

COPY ./requirements* /tmp/

RUN pip install -r /tmp/requirements-dev.txt \
    && addgroup -g ${GROUP_ID} ajobgroup \
    && adduser -u ${USER_ID} -D -s /bin/sh -h /tmp/ -H -G ajobgroup ajobuser

USER ajobuser
