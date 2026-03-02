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

import typing as tp

import pytest

from restalchemy.storage import exceptions

from genesis_core.compute.dm.models import MachinePool
from genesis_core.tests.functional import utils as test_utils


DictStrAny = tp.Dict[str, tp.Any]


class DriverSpecWithException(tp.TypedDict):
    driver_spec: tp.Optional[
        DictStrAny
    ]

    exception: tp.Optional[
        tp.Type[Exception]
    ]


DEFAULT_MACHINE_POOL_CONNECTION_URI = "qemu://system"
DEFAULT_DRIVER_SPEC_WITH_EXCEPTION = DriverSpecWithException(
    driver_spec={"connection_uri": DEFAULT_MACHINE_POOL_CONNECTION_URI},
    exception=None,
)


class PoolFactory(tp.Protocol):
    def __call__(self, *, driver_spec: DictStrAny) -> DictStrAny:
        ...


@pytest.mark.parametrize(
    "driver_specs_with_exceptions",
    [
        pytest.param(
            [
                DEFAULT_DRIVER_SPEC_WITH_EXCEPTION,
            ],
            id="single-insert"
        ),
        pytest.param(
            [
                DriverSpecWithException(driver_spec=None, exception=None),
            ],
            id="none-driver-spec",
        ),
        pytest.param(
            [
                DriverSpecWithException(driver_spec={}, exception=None),
            ],
            id="empty-dict-driver-spec",
        ),
        pytest.param(
            [
                DriverSpecWithException(
                    driver_spec={"connection_uri": None},
                    exception=None,
                ),
            ],
            id="empty-connection-uri-driver-spec",
        ),
        pytest.param(
            [
                DriverSpecWithException(driver_spec=None, exception=None),
                DriverSpecWithException(driver_spec=None, exception=None),
            ],
            id="allow-connection-uri-null-duplicate",
        ),
        pytest.param(
            [
                DEFAULT_DRIVER_SPEC_WITH_EXCEPTION,
                DriverSpecWithException(
                    driver_spec={
                        "connection_uri": DEFAULT_MACHINE_POOL_CONNECTION_URI,
                    },
                    exception=exceptions.ConflictRecords,
                )
            ],
            id="disallow-duplicate-connection-uri",
        ),
    ],
)
def test_connection_uri_idx(
    driver_specs_with_exceptions: tp.List[DriverSpecWithException],
    test_session: test_utils.AbstractSession,
    pool_factory: PoolFactory,
):
    for param in driver_specs_with_exceptions:
        machine_pool = MachinePool.restore_from_simple_view(
            **pool_factory(
                driver_spec=param["driver_spec"],
            )
        )

        if param["exception"] is None:
            machine_pool.insert(session=test_session)
        else:
            with pytest.raises(param["exception"]):
                machine_pool.insert(session=test_session)