#!/usr/bin/env python3
# webhook2kafka
# Copyright(C) 2018 Christoph Görn
#
# This program is free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


"""This will send all the GitHub webhooks to a Kafka topic."""

import os
import hmac
import logging
import json
import sys
from http import HTTPStatus


import daiquiri
import kafka
from kafka import KafkaProducer
from flask import Flask, Response, jsonify, make_response, request, current_app
from prometheus_flask_exporter import PrometheusMetrics

from cyborg_regidores import __version__ as cyborg_regidores_version
from cyborg_regidores.topic_names import (
    GITHUB_WEBHOOK_TOPIC_NAME,
    GITLAB_WEBHOOK_TOPIC_NAME,
    JIRA_WEBHOOK_TOPIC_NAME,
    TRELLO_WEBHOOK_TOPIC_NAME,
    GOOGLE_CHATBOT_TOPIC_NAME,
    AICOE_ACTIVITY_TOPIC_NAME,
)


_DEBUG = os.getenv("DEBUG", False)


daiquiri.setup()
_LOGGER = daiquiri.getLogger("webhook2kafka")
_LOGGER.setLevel(logging.DEBUG if _DEBUG else logging.INFO)

_KAFAK_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


app = Flask(__name__)
metrics = PrometheusMetrics(app)
metrics.info("cyborg_regidores_webhook2kafka_info", "Cyborg Regidores webhook2kafka", version=cyborg_regidores_version)


@app.after_request
def add_app_version(response):
    response.headers["X-Cyborg-Regidores"] = cyborg_regidores_version
    return response


@app.route("/")
def root():
    return f"This service is for Bots only, anyway, here is a tiny glimpse into what I am: v{cyborg_regidores_version}"


@app.route("/healthz")
@metrics.do_not_track()
def healthz():
    status_code = HTTPStatus.OK
    health = {"version": cyborg_regidores_version}

    return make_response(jsonify(health), status_code)


@app.route("/github", methods=["POST"])
def send_github_webhook_to_topic():
    """Entry point for github webhook."""
    resp = Response()
    payload = None
    status_code = HTTPStatus.OK

    event_type = request.headers.get("X-GitHub-Event")

    signature = request.headers.get("X-Hub-Signature")
    sha, signature = signature.split("=")

    secret = str.encode(current_app.config.get("GITHUB_WEBHOOK_SECRET"))

    hashhex = hmac.new(secret, request.data, digestmod="sha1").hexdigest()

    if hmac.compare_digest(hashhex, signature):
        payload = request.json
    else:
        _LOGGER.error(f"Webhook secret mismatch: me: {hashhex} != them: {signature}")
        return

    if payload is None:
        _LOGGER.error("GitHub webhook payload was empty")
        return resp, HTTPStatus.INTERNAL_SERVER_ERROR

    if event_type is None or event_type == "":
        _LOGGER.error("GitHub webhook event type was not provided")
        return resp, HTTPStatus.INTERNAL_SERVER_ERROR

    _publish(AICOE_ACTIVITY_TOPIC_NAME, {"event_type": event_type, "payload": payload})
    status_code = _publish(GITHUB_WEBHOOK_TOPIC_NAME, {"event_type": event_type, "payload": payload})

    return resp, status_code


@app.route("/gitlab", methods=["POST"])
def send_gitlab_webhook_to_topic():
    """Entry point for gitlab webhook."""
    resp = Response()
    payload = None
    status_code = HTTPStatus.OK

    payload = request.json

    if payload is None:
        _LOGGER.error("GitLab webhook payload was empty")
        return resp, HTTPStatus.INTERNAL_SERVER_ERROR

    event_type = payload["object_kind"]

    _publish(AICOE_ACTIVITY_TOPIC_NAME, {"event_type": event_type, "payload": payload})
    status_code = _publish(GITLAB_WEBHOOK_TOPIC_NAME, {"event_type": event_type, "payload": payload})

    return resp, status_code


@app.route("/trello", methods=["POST"])
def send_trello_webhook_to_topic():
    """Entry point for trello webhook."""
    resp = Response()
    payload = None
    status_code = HTTPStatus.OK

    payload = request.json

    if payload is None:
        _LOGGER.error("Trello webhook payload was empty")
        return resp, HTTPStatus.INTERNAL_SERVER_ERROR

    event_type = "trello-stub"  # TODO payload["object_kind"]

    _publish(AICOE_ACTIVITY_TOPIC_NAME, {"event_type": event_type, "payload": payload})
    status_code = _publish(TRELLO_WEBHOOK_TOPIC_NAME, {"event_type": event_type, "payload": payload})

    return resp, status_code


def _publish(topic: str, payload: dict) -> str:
    """Publish the given dict to topic."""
    producer = None
    status_code = HTTPStatus.OK

    if producer is None:
        _LOGGER.debug("KafkaProducer was not connected, trying to reconnect...")
        try:
            producer = KafkaProducer(
                bootstrap_servers=_KAFAK_BOOTSTRAP_SERVERS,
                acks=1,  # Wait for leader to write the record to its local log only.
                compression_type="gzip",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                security_protocol="SSL",
                ssl_cafile="secrets/data-hub-kafka-ca.crt",
            )
        except kafka.errors.NoBrokersAvailable as excptn:
            _LOGGER.debug("while trying to reconnect KafkaProducer: we failed...")
            _LOGGER.error(excptn)
            return HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        future = producer.send(topic, payload)
        result = future.get(timeout=6)
        _LOGGER.debug(result)
    except AttributeError as excptn:
        _LOGGER.debug(excptn)
        status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    except (kafka.errors.NotLeaderForPartitionError, kafka.errors.KafkaTimeoutError) as excptn:
        _LOGGER.error(excptn)
        producer.close()
        producer = None

        status_code = HTTPStatus.INTERNAL_SERVER_ERROR

    return status_code


if __name__ == "__main__":
    _LOGGER.info(f"Cyborg Regidores webhook2kafka v{cyborg_regidores_version} started.")
    _LOGGER.debug("DEBUG mode is enabled!")

    app.config["GITHUB_WEBHOOK_SECRET"] = os.environ.get("GITHUB_WEBHOOK_SECRET")

    _LOGGER.info(f"running Flask application now...")
    app.run(host="0.0.0.0", port=8080, debug=_DEBUG)
