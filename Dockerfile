# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7

ARG PYTHON_VERSION=3.12.4
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

#TODO: change to build args later
ENV CONN_DETAILS='host=rc1b-xx946i4v217yyiv4.mdb.yandexcloud.net,rc1d-5dkpuccnhyughi8n.mdb.yandexcloud.net port=6432 sslmode=verify-full dbname=test_wb user=jbcorel password=12345678 target_session_attrs=read-write'

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Switch to the non-privileged user to run the application.

RUN apt-get update && \
    apt-get install wget postgresql-client --yes && \
    mkdir -p ~/.postgresql && \
    wget "https://storage.yandexcloud.net/cloud-certs/CA.pem" \
        --output-document ~/.postgresql/root.crt && \
    chmod 0600 ~/.postgresql/root.crt
# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
CMD uvicorn 'app.api:app' --host=0.0.0.0 --port=8000

