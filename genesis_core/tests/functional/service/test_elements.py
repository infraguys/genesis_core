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

from gcl_iam.tests.functional import clients as iam_clients

from genesis_core.elements.services import builders


class TestSecretsServiceBuilder:
    def setup_method(self) -> None:
        # Run service
        self._service = builders.ElementManagerBuilder()

    def teardown_method(self) -> None:
        pass

    def test_element_manager_builder(
        self,
        password_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        self._service._iteration()
