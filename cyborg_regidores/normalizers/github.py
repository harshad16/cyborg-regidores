#!/usr/bin/env python3
# cyborg-regidores
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


"""The Regidor promotes social participation and reforms community regulations."""


import os
import logging
import daiquiri
import json

import kafka
from kafka import KafkaConsumer, KafkaProducer

from .base import Normalizer, threaded
from ..topic_names import NORMALIZED_EVENTS_TOPIC_NAME

daiquiri.setup()
_LOGGER = daiquiri.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG if os.getenv("DEBUG", False) else logging.INFO)


class GitHubNormalizer(Normalizer):
    """The Normalizer is used to convert GitHub webhook events to a common format.
    
    A normalized Push Event looks like:
    ```
    {
        "ref": "refs/heads/master",
        "commits": [{
            "id": "b6568db1bc1dcd7f8b4d5a946b0b91f9dacd7327",
            "message": "Update Catalan translation to e38cb41.",
            "timestamp": "2011-12-12T14:27:31+02:00",
            "author": {
                "name": "Jordi Mallach",
                "email": "jordi@softcatala.org"
            }
        }],
        "repository": {
            "url": "http://example.com/mike/diaspora.git"
        }
    }
    ```
    
    """

    bootstrap_servers = None
    from_topic = None
    to_topic = None
    producer = None

    def __init__(self, bootstrap_servers=None, from_topic: str = None, to_topic: str = None):
        """Initialize the GitHub Normalizer."""
        if from_topic is None or to_topic is None or from_topic == "" or to_topic == "":
            _LOGGER.error("from_topic and to_topic must not be empty")

        self.from_topic = from_topic
        self.to_topic = to_topic
        self.bootstrap_servers = bootstrap_servers

        self.consumer = KafkaConsumer(
            from_topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda v: json.loads(v),
            security_protocol="SSL",
            ssl_check_hostname=False,
            ssl_cafile="conf/ca.pem",
            group_id=None,
        )

        _LOGGER.debug("GitHubNormalizer from %r to %r initialized!", from_topic, to_topic)

    def _publish(self, event: dict):
        """Publish the normalized event to a Kafka topic."""
        if self.producer is None:
            _LOGGER.debug("KafkaProducer was not connected, trying to reconnect...")
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
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
            return

        try:
            self.producer.send(NORMALIZED_EVENTS_TOPIC_NAME, event)
        except AttributeError as excptn:
            _LOGGER.debug(excptn)
        except (kafka.errors.NotLeaderForPartitionError, kafka.errors.KafkaTimeoutError) as excptn:
            _LOGGER.error(excptn)
            self.producer.close()
            self.producer = None

    @threaded
    def filter(self):
        """This will read events from_topic, filter them and write to_topic."""
        for msg in self.consumer:
            # TODO if we cant send to_topic or other error, the message from_topic should not be ack'd
            event = msg.value
            normalized_event = {}

            _LOGGER.debug("GitHub Push Event %r", json.dumps(event))

            if event["event_type"] == "push":
                normalized_event["ref"] = event["payload"]["ref"]
                normalized_event["repository"] = {}
                normalized_event["repository"]["url"] = event["payload"]["repository"]["html_url"]
                normalized_event["commits"] = []

                for commit in event["payload"]["commits"]:
                    normalized_commit = {}
                    normalized_commit["id"] = commit["id"]
                    normalized_commit["message"] = commit["message"]
                    normalized_commit["timestamp"] = commit["timestamp"]
                    normalized_commit["author"] = commit["author"]
                    normalized_event["commits"].append(normalized_commit)

            _LOGGER.debug("Normalized GitHub Push Event %r", json.dumps(normalized_event))

            self._publish(normalized_event)

    def stop(self):
        """This will stop the filter thread."""
        pass  # TODO