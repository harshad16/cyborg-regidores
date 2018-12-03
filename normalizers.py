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


import daiquiri
import kafka
from kafka import KafkaConsumer

from cyborg_regidores import __version__ as cyborg_regidores_version
from cyborg_regidores.topic_names import GITHUB_WEBHOOK_TOPIC_NAME, GITLAB_WEBHOOK_TOPIC_NAME
from cyborg_regidores.normalizers.github import GitHubNormalizer
from cyborg_regidores.normalizers.gitlab import GitLabNormalizer


DEBUG = os.getenv("DEBUG", True)


daiquiri.setup()
_LOGGER = daiquiri.getLogger("webhook2kafka")
_LOGGER.setLevel(logging.DEBUG if DEBUG else logging.INFO)

_KAFAK_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


if __name__ == "__main__":
    _LOGGER.info(f"Cyborg Regidores Normalizers v{cyborg_regidores_version}.")
    _LOGGER.debug("DEBUG mode is enabled!")

    github_normalizer = GitHubNormalizer(
        bootstrap_servers=_KAFAK_BOOTSTRAP_SERVERS,
        from_topic=GITHUB_WEBHOOK_TOPIC_NAME,
        to_topic="cyborg_regidores_events",
    )
    github_normalizer.filter()

    gitlab_cee_normalizer = GitLabNormalizer(
        bootstrap_servers=_KAFAK_BOOTSTRAP_SERVERS,
        from_topic=GITLAB_WEBHOOK_TOPIC_NAME,
        to_topic="cyborg_regidores_events",
    )
    gitlab_cee_normalizer.filter()
