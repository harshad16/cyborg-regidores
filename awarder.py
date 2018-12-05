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
import ssl

from datetime import timedelta


import daiquiri
import faust

from cyborg_regidores import __version__ as cyborg_regidores_version
from cyborg_regidores.topic_names import NORMALIZED_EVENTS_TOPIC_NAME
from cyborg_regidores.event_types import SocialEvent

DEBUG = os.getenv("DEBUG", True)


ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile="conf/ca.pem")

daiquiri.setup()
_LOGGER = daiquiri.getLogger("awarder")
_LOGGER.setLevel(logging.DEBUG if DEBUG else logging.INFO)

_KAFAK_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


app = faust.App("cyborg_regidores_awarder", broker=_KAFAK_BOOTSTRAP_SERVERS, ssl_context=ssl_context)
pull_request_badge = app.Table("pull_request_badge", default=int).tumbling(
    timedelta(hours=24), expires=timedelta(hours=48)
)
pull_requests = app.Table("pull_requests", default=int).tumbling(timedelta(hours=24), expires=timedelta(hours=48))

social_events = app.topic(NORMALIZED_EVENTS_TOPIC_NAME, value_type=SocialEvent)


@app.agent(social_events)
async def aggregate_pull_requests(events):
    # values in this streams are URLs as strings.
    async for pull_request in events:
        if pull_request.event_type == "pull_request":
            # increment one to all windows this page URL fall into.
            pull_requests[pull_request.user_name] += 1

            if pull_requests[pull_request.user_name].now() >= 2:
                # PR user is trending for current processing time window
                print(f"Trending now: {pull_request}")

            if pull_requests[pull_request.user_name].current() >= 2:
                # PR user would be trending in the current event's time window
                print(f"Trending when event happened: {pull_request}")

            if (
                pull_requests[pull_request.user_name].delta(timedelta(minutes=30))
                > pull_requests[pull_request.user_name].now()
            ):
                print(f"Less popular compared to 30 minutes back: {pull_request}")


# @app.agent(social_events)
async def process(events):
    async for event in events:
        print(f"{event}")

        if event.action == "open":
            # the following is a little verbose but the pattern used to write the changelog to
            # kafka, see https://faust.readthedocs.io/en/latest/userguide/tables.html#the-changelog
            _pull_request_badge = pull_request_badge[event.user_name]
            _pull_request_badge = 1
            pull_request_badge[event.user_name] = _pull_request_badge


if __name__ == "__main__":
    app.main()
