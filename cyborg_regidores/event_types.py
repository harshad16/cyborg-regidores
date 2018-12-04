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


"""The Faust Record types we are using."""


from datetime import datetime

import faust


class SocialEvent(faust.Record, isodates=True, serializer="json"):
    event_type: str
    action: str
    user_name: str
    repository_url: str
    pull_request_url: str = None
    issue_url: str = None
    created_at: datetime = None
    updated_at: datetime = None

