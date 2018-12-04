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

import daiquiri
import faust

from cyborg_regidores import __version__ as cyborg_regidores_version
from cyborg_regidores.topic_names import NORMALIZED_EVENTS_TOPIC_NAME
from cyborg_regidores.event_types import SocialEvent

DEBUG = os.getenv("DEBUG", True)


ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile="conf/ca.pem")

daiquiri.setup()
_LOGGER = daiquiri.getLogger("webhook2kafka")
_LOGGER.setLevel(logging.DEBUG if DEBUG else logging.INFO)

_KAFAK_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


app = faust.App("granter", broker=_KAFAK_BOOTSTRAP_SERVERS, ssl_context=ssl_context)
table = app.Table("awards", default=int)


topic = app.topic(NORMALIZED_EVENTS_TOPIC_NAME, value_type=SocialEvent)


@app.agent(topic)
async def process(stream):
    async for item in stream:
        print(f"{item}")


if __name__ == "__main__":
    app.main()
