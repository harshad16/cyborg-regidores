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


class GitLabNormalizer(Normalizer):
    """The Normalizer is used to convert GitLab webhook events to a common format."""

    bootstrap_servers = None
    from_topic = None
    to_topic = None
    producer = None

    def __init__(self, bootstrap_servers=None, from_topic: str = None, to_topic: str = None):
        """Initialize the GitLab Normalizer."""
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
            group_id="github_normalizer",
            auto_offset_reset="earliest",
        )

        _LOGGER.debug("GitLabNormalizer from %r to %r initialized!", from_topic, to_topic)

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
            event_type = event["object_kind"]
            normalized_event = None

            _LOGGER.debug("GitLab Event %r", json.dumps(event))

            if event_type == "push":
                normalized_event = {}
                payload = event["payload"]

                normalized_event["event_type"] = "push"
                normalized_event["user_name"] = payload["user_username"]

                normalized_event["repository_url"] = event["payload"]["repository"]["url"]
                normalized_event["commits"] = []

                for commit in event["payload"]["commits"]:
                    normalized_commit = {}
                    normalized_commit["id"] = commit["id"]
                    normalized_commit["message"] = commit["message"]
                    normalized_commit["timestamp"] = commit["timestamp"]
                    normalized_commit["author_email"] = commit["author"]["email"]
                    normalized_event["commits"].append(normalized_commit)

                _LOGGER.debug("Normalized GitLab Push Event %r", json.dumps(normalized_event))

                self._publish(normalized_event)
            elif event_type == "merge_request":
                normalized_event = {}
                payload = event["payload"]

                normalized_event["event_type"] = "pull_request"
                normalized_event["action"] = payload["object_attributes"]["action"]
                normalized_event["user_name"] = payload["user"]["username"]

                normalized_event["created_at"] = payload["object_attributes"]["created_at"]
                normalized_event["updated_at"] = payload["object_attributes"]["updated_at"]

                normalized_event["repository_url"] = payload["repository"]["url"]
                normalized_event["pull_request_url"] = payload["object_attributes"]["url"]

                _LOGGER.debug("Normalized GitLab Pull Request Event %r", json.dumps(normalized_event))
            elif event["event_type"] == "issues":
                normalized_event = {}
                payload = event["payload"]

                normalized_event["event_type"] = "issues"
                normalized_event["action"] = payload["object_attributes"]["action"]
                normalized_event["user_name"] = payload["user"]["username"]

                normalized_event["created_at"] = payload["object_attributes"]["created_at"]
                normalized_event["updated_at"] = payload["object_attributes"]["updated_at"]

                normalized_event["repository_url"] = payload["repository"]["url"]
                normalized_event["issue_url"] = payload["object_attributes"]["url"]

                _LOGGER.debug("Normalized GitHub Issue Event %r", json.dumps(normalized_event))

            if normalized_event is not None:
                self._publish(normalized_event)

    def stop(self):
        """This will stop the filter thread."""
        pass  # TODO
