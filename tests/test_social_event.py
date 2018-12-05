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


import pytest

from cyborg_regidores.event_types import SocialEvent


@pytest.fixture
def GoodPullRequest():
    normalized_event = {}

    normalized_event["event_type"] = "pull_request"
    normalized_event["action"] = "open"
    normalized_event["user_name"] = "sesheta"

    normalized_event["created_at"] = "2018-12-03T15:11:03Z"
    normalized_event["updated_at"] = "2018-12-03T19:03:41Z"

    normalized_event["repository_url"] = "https://github.com/thoth-station/package-releases-job"
    normalized_event["pull_request_url"] = "https://github.com/thoth-station/package-releases-job/pull/128"


class TestSocialEvent(object):
    def test_init_from_dict(self):
        se = SocialEvent(GoodPullRequest)

        x = "this"
        assert "h" in x

