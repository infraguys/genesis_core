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

import uuid as sys_uuid


ELEMENT_NAMESPACE = sys_uuid.UUID("f277e88a-cd58-4c33-a0c3-23a1086a53b7")
UUID_PREFIX = "12345678"


def clear_parameters(resource_link):
    parts = resource_link.split(".")
    return ".".join(parts[:-1] + [parts[-1].split(":")[0]])


class ResourceLink:

    def __init__(self, link_string):
        super().__init__()
        self._link_string = link_string

    @property
    def location(self):
        return clear_parameters(self._link_string)

    @property
    def parameter(self):
        return self._link_string.split(".")[-1]


def get_element_uuid(element_name, element_version):
    tmp = str(
        sys_uuid.uuid5(
            ELEMENT_NAMESPACE,
            f"{element_name}-{element_version}",
        )
    )
    return sys_uuid.UUID(f"{UUID_PREFIX}{tmp[8:]}")


def get_project_id():
    # return sys_uuid.UUID(f"{UUID_PREFIX}{str(sys_uuid.uuid4())[8:]}")
    return sys_uuid.UUID(
        f"{UUID_PREFIX}{str('00000000-0000-0000-0000-000000000000')[8:]}"
    )


def get_required_field(data, field_name):
    if field_name not in data:
        raise ValueError(
            f"required field '{field_name}' is missing in the provided"
            f" data: {data}"
        )
    return data[field_name]
