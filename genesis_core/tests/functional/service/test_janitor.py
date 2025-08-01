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

import datetime

import pytest

from genesis_core.janitor import service
from genesis_core.user_api.iam.dm import models


class TestExpiredEmailConfirmationCodeJanitorService:

    def setup_method(self) -> None:
        # Run service
        self._service = service.ExpiredEmailConfirmationCodeJanitorService()

    def teardown_method(self) -> None:
        pass

    def test_service_runs(self, user_api):
        self._service._iteration()

    @pytest.mark.parametrize(
        "code_made_at",
        [
            datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc),
            None,
        ],
    )
    def test_service_wipes_bad_codes(self, auth_test1_user, code_made_at):
        user = models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        user.reset_confirmation_code()
        user.confirmation_code_made_at = code_made_at
        user.save()

        self._service._iteration()

        user = models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        assert user.confirmation_code is None
        assert user.confirmation_code_made_at is None

    def test_service_keeps_active_codes(self, auth_test1_user):
        user = models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        user.reset_confirmation_code()
        # Check the code is valid right now:
        assert user.check_confirmation_code(user.confirmation_code)

        self._service._iteration()

        user_after_cleanup = models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        assert user_after_cleanup.confirmation_code == user.confirmation_code
        assert (
            user_after_cleanup.confirmation_code_made_at
            == user.confirmation_code_made_at
        )
