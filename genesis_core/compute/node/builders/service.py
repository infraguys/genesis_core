#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from __future__ import annotations

import logging
import collections
import uuid as sys_uuid
import typing as tp

from restalchemy.common import contexts
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.dm import filters as dm_filters
from gcl_looper.services import basic
from gcl_sdk.agents.universal.dm import models as ua_models
from gcl_sdk.agents.universal.services import builder as sdk_builder
from gcl_sdk.agents.universal.clients.orch import base as orch_base
from gcl_sdk.agents.universal.clients.orch import exceptions as orch_exc

from genesis_core.compute.dm import models
from genesis_core.common import utils
from genesis_core.compute import constants as nc

LOG = logging.getLogger(__name__)


class Node(models.Node, ua_models.InstanceMixin):

    @classmethod
    def get_resource_kind(cls) -> str:
        return "node"


class NodeBuilderService(sdk_builder.UniversalBuilderService):

    def __init__(
        self,
        iter_min_period: int = 1,
        iter_pause: float = 0.1,
    ) -> None:
        super().__init__(
            Node,
            iter_min_period=iter_min_period,
            iter_pause=iter_pause,
        )
