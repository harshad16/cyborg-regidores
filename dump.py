#!/usr/bin/env python3
# dump
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


"""This will dump all the GitHub webhooks on a Kafka topic."""

import os
import logging
import json


import daiquiri
import kafka
from kafka import KafkaConsumer


__version__ = "0.1.0-dev"


DEBUG = os.getenv("DEBUG", True)
GITHUB_WEBHOOK_TOPIC_NAME = "cyborg_regidores_github"

daiquiri.setup()
_LOGGER = daiquiri.getLogger("webhook2kafka")
_LOGGER.setLevel(logging.DEBUG if DEBUG else logging.INFO)

_KAFAK_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


if __name__ == "__main__":
    _LOGGER.info(f"Cyborg Regidores dump v{__version__}.")
    _LOGGER.debug("DEBUG mode is enabled!")

    # let's get all that we got...
    consumer = KafkaConsumer(
        GITHUB_WEBHOOK_TOPIC_NAME,
        bootstrap_servers=_KAFAK_BOOTSTRAP_SERVERS,
        value_deserializer=lambda v: json.loads(v),
        security_protocol="SSL",
        ssl_check_hostname=False,
        ssl_cafile="conf/ca.pem",
        group_id=None,
        auto_offset_reset="earliest",
    )

    for msg in consumer:
        print(msg)
