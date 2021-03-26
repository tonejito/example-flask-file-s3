# Containerfile for the Flask image tool

FROM python:3.8-alpine AS base

ENV ENV=/etc/profile \
    HOME=/root
COPY config/motd /etc/motd
RUN echo "cat /etc/motd" > /etc/profile.d/motd.sh

FROM base AS app

ENV FLASK_APP=app.py \
    FLASK_ENV=development \
    FLASK_DIR=/opt \
    HOST=0.0.0.0 \
    PORT=5000
ENV UPLOAD_FOLDER=${FLASK_DIR}/storage

EXPOSE ${PORT}

WORKDIR ${FLASK_DIR}

COPY app.py requirements.txt ${FLASK_DIR}
COPY static/ ${FLASK_DIR}/static/
COPY templates/ ${FLASK_DIR}/templates/

RUN mkdir -vp ${UPLOAD_FOLDER} && \
    chmod -c a+rx,ug+ws,o-w ${UPLOAD_FOLDER} && \
    pip config --global set global.progress_bar off && \
    pip install --requirement requirements.txt

# CMD flask run --host=${HOST} --port ${PORT} --reload --no-debugger --eager-loading --with-threads
CMD gunicorn app:app --bind ${HOST}:${PORT} --reload --preload --capture-output --log-level info --access-logfile - --error-logfile -
