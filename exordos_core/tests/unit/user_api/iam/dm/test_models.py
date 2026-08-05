#    Copyright 2026 Genesis Corporation.
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

from types import SimpleNamespace
from unittest import mock

from exordos_core.user_api.iam.dm import models


def test_project_list_my_returns_each_project_once():
    first_project = SimpleNamespace(uuid="project-1")
    duplicate_project = SimpleNamespace(uuid="project-1")
    second_project = SimpleNamespace(uuid="project-2")
    role_bindings = [
        SimpleNamespace(project=first_project),
        SimpleNamespace(project=duplicate_project),
        SimpleNamespace(project=second_project),
    ]

    with (
        mock.patch.object(models.User, "me"),
        mock.patch.object(
            type(models.RoleBinding.objects),
            "get_all",
            return_value=role_bindings,
        ),
    ):
        projects = models.Project.list_my()

    assert projects == [first_project, second_project]
