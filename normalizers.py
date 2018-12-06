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


"""This will normalize all the Event on one Kafka topic."""

import os
import logging
import json
import ssl


import daiquiri
import faust

from cyborg_regidores import __version__ as cyborg_regidores_version
from cyborg_regidores.topic_names import (
    GITHUB_WEBHOOK_TOPIC_NAME,
    GITLAB_WEBHOOK_TOPIC_NAME,
    TRELLO_WEBHOOK_TOPIC_NAME,
    NORMALIZED_EVENTS_TOPIC_NAME,
)
from cyborg_regidores.event_types import SocialEvent

DEBUG = os.getenv("DEBUG", True)


daiquiri.setup()
_LOGGER = daiquiri.getLogger("normalizers")
_LOGGER.setLevel(logging.DEBUG if DEBUG else logging.INFO)

_KAFAK_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
_KAFKA_TOPIC_RETENTION_TIME_SECONDS = 60 * 60 * 24 * 45

ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile="conf/ca.pem")
app = faust.App(
    "cyborg_regidores_normalizers",
    broker=_KAFAK_BOOTSTRAP_SERVERS,
    value_serializer="json",
    ssl_context=ssl_context,
    web_enabled=False,
)
github_topic = app.topic(GITHUB_WEBHOOK_TOPIC_NAME, retention=_KAFKA_TOPIC_RETENTION_TIME_SECONDS)
gitlab_topic = app.topic(GITLAB_WEBHOOK_TOPIC_NAME, retention=_KAFKA_TOPIC_RETENTION_TIME_SECONDS)
trello_topic = app.topic(TRELLO_WEBHOOK_TOPIC_NAME, retention=_KAFKA_TOPIC_RETENTION_TIME_SECONDS)
normalized_events_topic = app.topic(NORMALIZED_EVENTS_TOPIC_NAME, retention=_KAFKA_TOPIC_RETENTION_TIME_SECONDS)


@app.agent(github_topic, sink=[normalized_events_topic])
async def github_normalize(events):
    async for event in events:
        normalized_event = None

        try:
            if event["event_type"] == "push":
                normalized_event = {}
                payload = event["payload"]

                normalized_event["event_type"] = "push"
                normalized_event["user_name"] = payload["pusher"]["name"]

                normalized_event["repository_url"] = event["payload"]["repository"]["html_url"]
                normalized_event["commits"] = []

                for commit in event["payload"]["commits"]:
                    normalized_commit = {}
                    normalized_commit["id"] = commit["id"]
                    normalized_commit["message"] = commit["message"]
                    normalized_commit["timestamp"] = commit["timestamp"]
                    normalized_commit["author_email"] = commit["author"]["email"]
                    normalized_event["commits"].append(normalized_commit)

                _LOGGER.debug("Normalized GitHub Push Event %r", json.dumps(normalized_event))

            elif event["event_type"] == "pull_request":
                normalized_event = {}
                payload = event["payload"]

                normalized_event["event_type"] = "pull_request"
                normalized_event["action"] = payload["action"]
                normalized_event["user_name"] = payload["pull_request"]["user"]["login"]

                normalized_event["created_at"] = payload["pull_request"]["created_at"]
                normalized_event["updated_at"] = payload["pull_request"]["updated_at"]

                normalized_event["repository_url"] = payload["repository"]["html_url"]
                normalized_event["pull_request_url"] = payload["pull_request"]["html_url"]

                _LOGGER.debug("Normalized GitHub Pull Request Event %r", json.dumps(normalized_event))

            elif event["event_type"] == "issues":
                normalized_event = {}
                payload = event["payload"]

                normalized_event["event_type"] = "issues"
                normalized_event["action"] = payload["action"]
                normalized_event["user_name"] = payload["issue"]["user"]["login"]

                normalized_event["created_at"] = payload["issue"]["created_at"]
                normalized_event["updated_at"] = payload["issue"]["updated_at"]

                normalized_event["repository_url"] = payload["repository"]["html_url"]
                normalized_event["issue_url"] = payload["issue"]["html_url"]

                _LOGGER.debug("Normalized GitHub Issue Event %r", json.dumps(normalized_event))

        except KeyError as excptn:
            _LOGGER.error("github_normalize: %r", excptn)

        if normalized_event is not None:
            try:
                normalized_social_event = SocialEvent(**normalized_event)

                yield normalized_social_event

            except TypeError as excptn:
                _LOGGER.error("github_normalize: sending normalized SociaEvent(): %r", excptn)


@app.agent(gitlab_topic, sink=[normalized_events_topic])
async def gitlab_normalize(events):
    async for event in events:
        normalized_event = None

        try:
            if event["event_type"] == "push":
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

            elif event["event_type"] == "merge_request":
                normalized_event = {}
                payload = event["payload"]

                normalized_event["event_type"] = "pull_request"
                normalized_event["action"] = payload["object_attributes"]["action"]
                normalized_event["user_name"] = payload["user"]["username"]

                normalized_event["created_at"] = payload["object_attributes"]["created_at"]
                normalized_event["updated_at"] = payload["object_attributes"]["updated_at"]

                normalized_event["repository_url"] = payload["repository"]["url"]
                normalized_event["pull_request_url"] = payload["object_attributes"]["url"]

                _LOGGER.debug("Normalized GitLab Merge Request Event %r", json.dumps(normalized_event))
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

        except KeyError as excptn:
            _LOGGER.error("gitlab_normalize: %r", excptn)

        if normalized_event is not None:
            try:
                normalized_social_event = SocialEvent(**normalized_event)

                yield normalized_social_event

            except TypeError as excptn:
                _LOGGER.error("gitlab_normalize: sending normalized SociaEvent(): %r", excptn)


if __name__ == "__main__":
    _LOGGER.info(f"Cyborg Regidores Normalizers v{cyborg_regidores_version}.")
    _LOGGER.debug("DEBUG mode is enabled!")

    app.main()
