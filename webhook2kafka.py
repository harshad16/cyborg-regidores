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
from http import HTTPStatus


import daiquiri
import kafka
from kafka import KafkaProducer
from flask import Flask, Response, jsonify, make_response, request, current_app

__version__ = "0.1.0-dev"


DEBUG = os.getenv("DEBUG", False)
GITHUB_WEBHOOK_TOPIC_NAME = "cyborg_regidores_github"

daiquiri.setup()
_LOGGER = daiquiri.getLogger("webhook2kafka")
_LOGGER.setLevel(logging.DEBUG if DEBUG else logging.INFO)

_KAFAK_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


app = Flask(__name__)
producer = None


@app.after_request
def add_app_version(response):
    response.headers["X-Cyborg-Regidores"] = __version__
    return response


@app.route("/")
def root():
    return "This service is for Bots only!"


@app.route("/healthz")
def healthz():
    status_code = HTTPStatus.OK
    health = {"version": __version__}

    if producer is None:
        status_code = HTTPStatus.SERVICE_UNAVAILABLE
        health["status"] = {"kafka": "NoBrokersAvailable"}

    return make_response(jsonify(health), status_code)


@app.route("/github", methods=["POST"])
def send_github_webhook_to_topic():
    """Entry point for github webhook."""
    global producer
    resp = Response()
    payload = None
    status_code = HTTPStatus.OK

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

    if producer is None:
        _LOGGER.debug("KafkaProducer was not connected, trying to reconnect...")
        try:
            producer = KafkaProducer(
                bootstrap_servers=_KAFAK_BOOTSTRAP_SERVERS,
                acks=1,  # Wait for leader to write the record to its local log only.
                compression_type="gzip",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                security_protocol="SSL",
                ssl_check_hostname=False,
                ssl_cafile="conf/ca.pem",
            )
        except kafka.errors.NoBrokersAvailable as excptn:
            _LOGGER.debug("while trying to reconnect KafkaProducer: we failed...")
            _LOGGER.error(excptn)
            return resp, HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        future = producer.send(GITHUB_WEBHOOK_TOPIC_NAME, payload)
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

    return resp, status_code


if __name__ == "__main__":
    _LOGGER.info(f"Cyborg Regidores webhook2kafka v{__version__} started.")
    _LOGGER.debug("DEBUG mode is enabled!")

    app.config["GITHUB_WEBHOOK_SECRET"] = os.environ.get("GITHUB_WEBHOOK_SECRET")

    try:
        producer = KafkaProducer(
            bootstrap_servers=_KAFAK_BOOTSTRAP_SERVERS,
            acks=1,  # Wait for leader to write the record to its local log only.
            compression_type="gzip",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            security_protocol="SSL",
            ssl_check_hostname=False,
            ssl_cafile="conf/ca.pem",
        )
    except kafka.errors.NoBrokersAvailable as excptn:
        _LOGGER.error(excptn)

    _LOGGER.info(f"running Flask application now...")
    app.run(host="0.0.0.0", port=8080, debug=DEBUG)
