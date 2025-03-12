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

import typing as tp
import uuid as sys_uuid
from importlib.metadata import entry_points

from gcl_iam import algorithms
from restalchemy.common import contexts
from restalchemy.dm import filters as dm_filters

from genesis_core.common import constants as c
from genesis_core.user_api.iam import constants as iam_c


def node_uuid(path: str = c.NODE_UUID_PATH) -> sys_uuid.UUID:
    with open(path, "r") as f:
        return sys_uuid.UUID(f.read().strip())


def load_from_entry_point(group: str, name: str) -> tp.Any:
    """Load class from entry points."""
    for ep in entry_points():
        if ep.group == group and ep.name == name:
            return ep.load()

    raise RuntimeError(f"No class '{name}' found in entry points {group}")


def load_group_from_entry_point(group: str) -> tp.Any:
    """Load class from entry points."""
    return [e for e in entry_points(group=group)]


def get_context_storage(
    global_salt: str,
    token_algorithm: algorithms.AbstractAlgorithm,
) -> contexts.Storage:
    return contexts.Storage(
        data={
            iam_c.STORAGE_KEY_IAM_GLOBAL_SALT: {
                "value": global_salt,
                "read_only": True,
            },
            iam_c.STORAGE_KEY_IAM_TOKEN_ENCRYPTION_ALGORITHM: {
                "value": token_algorithm,
                "read_only": True,
            },
        }
    )


def remove_all_dm(dm_class, filters, session=None, **kwargs):
    for dm in dm_class.objects.get_all(filters=filters, session=session):
        dm.delete(session=session, **kwargs)


def remove_nested_dm(
    dm_class, parent_field_name, parent, session=None, **kwargs
):
    remove_all_dm(
        dm_class,
        filters={parent_field_name: dm_filters.EQ(parent)},
        session=session,
        **kwargs,
    )
