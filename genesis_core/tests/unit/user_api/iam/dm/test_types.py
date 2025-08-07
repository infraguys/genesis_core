# Copyright 2025 Genesis Corporation
#
# All Rights Reserved.
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

import pytest

from genesis_core.user_api.iam.dm import types


class TestUsernameTestCase:

    @pytest.fixture
    def test_instance(self):
        return types.Username(min_length=1, max_length=20)

    @pytest.fixture(
        scope="function",
        params=[
            ("u", True),
            ("用户123!", True),
            ("test+user@domain.com", False),
            ("a#b$c%&'*", True),
            ("~underscore_", True),
            ("john.doe{2023}", True),
            ("=equal-sign", True),
            ("slash/test", True),
            ("question?mark", True),
            ("caret^symbol", True),
            ("back`tick", True),
            ("pipe|symbol", True),
            ("tilde~wave", True),
            ("dash-test", True),
            ("123.45@domain", False),
            ("أحمد_2023", True),
            ("", False),
            (" space ", False),
            ("two words", True),  # " " space is allowed
            ("emoji😊", False),
            ("percent%age", True),  # "%" is allowed
            ("invalid/", True),  # "/" is allowed
            ("semicolon;test", False),
            ('quote"mark', False),
            ("bracket(test)", False),
            ("angle<tag", False),
            ("comma,separated", False),
            ("dash-", True),  # trailing "-" dash is allowed
            ("a\nb", False),
        ],
    )
    def username_values(self, request):
        return request.param

    def test_validate(self, test_instance: types.Username, username_values):
        value, expected_result = username_values

        result = test_instance.validate(value)

        assert result is expected_result


class TestNameTestCase:

    @pytest.fixture
    def test_instance(self):
        return types.Name(min_length=1, max_length=20)

    @pytest.fixture(
        scope="function",
        params=[
            ("u", True),
            ("用户123!", False),
            ("用户", True),
            ("test+user@domain.com", False),
            ("a#b$c%&'*", False),
            ("~underscore_", False),
            ("john.doe{2023}", False),
            ("=equal-sign", False),
            ("slash/test", False),
            ("question?mark", False),
            ("caret^symbol", False),
            ("back`tick", True),
            ("back'tick", True),
            ("back tick", True),
            ("back tick ", False),
            (" back tick", False),
            ("pipe|symbol", False),
            ("tilde~wave", False),
            ("dash-test", True),
            ("123.45@domain", False),
            ("أحمد_2023", False),
            ("", False),
            (" space ", False),
            ("two words", True),
            ("emoji😊", False),
            ("percent%age", False),
            ("invalid/", False),
            ("semicolon;test", False),
            ('quote"mark', False),
            ("bracket(test)", False),
            ("angle<tag", False),
            ("comma,separated", False),
            ("dash-", False),
            ("@start-with", False),
            ("user@", False),
            ("a\nb", False),
        ],
    )
    def username_values(self, request):
        return request.param

    def test_validate(self, test_instance: types.Username, username_values):
        value, expected_result = username_values

        result = test_instance.validate(value)

        assert result is expected_result
