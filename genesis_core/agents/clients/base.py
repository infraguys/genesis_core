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
from urllib.parse import urljoin

import bazooka
from bazooka import exceptions as bazooka_exc
from restalchemy.dm import models


class CollectionBaseModelClient:
    ACTIONS_KEY = "actions"
    INVOKE_KEY = "invoke"

    __collection_url__: str | None = None
    __model__: tp.Type[models.SimpleViewMixin] = None
    __resource_client__: tp.Type["ResourceBaseModelClient"] = None
    __parent__: str | None = None

    def __init__(
        self,
        base_url: str,
        http_client: bazooka.Client | None = None,
    ) -> None:
        self._http_client = http_client or bazooka.Client()
        self._base_url = base_url

    def __call__(
        self, resource_uuid: sys_uuid.UUID
    ) -> "ResourceBaseModelClient":
        if self.__resource_client__ is None:
            raise ValueError("Resource client is not defined")
        return self.__resource_client__(self, resource_uuid, self._http_client)

    def _collection_url(self):
        if not self._base_url.endswith(
            "/"
        ) and not self.__collection_url__.startswith("/"):
            return self._base_url + "/" + self.__collection_url__
        return self._base_url + self.__collection_url__

    def resource_url(self, uuid: sys_uuid.UUID):
        return urljoin(self._collection_url(), str(uuid))

    def get(self, uuid: sys_uuid.UUID) -> models.SimpleViewMixin:
        url = self.resource_url(uuid)
        resp = self._http_client.get(url)
        return self.__model__.restore_from_simple_view(**resp.json())

    def filter(
        self, **filters: tp.Dict[str, tp.Any]
    ) -> models.SimpleViewMixin:
        resp = self._http_client.get(self._collection_url(), params=filters)
        return [
            self.__model__.restore_from_simple_view(**o) for o in resp.json()
        ]

    def create(self, object: models.SimpleViewMixin) -> models.SimpleViewMixin:
        skip = tuple() if self.__parent__ is None else (self.__parent__,)
        data = object.dump_to_simple_view(skip=skip)
        resp = self._http_client.post(self._collection_url(), json=data)
        return self.__model__.restore_from_simple_view(**resp.json())

    def update(
        self, uuid: sys_uuid.UUID, **params: tp.Dict[str, tp.Any]
    ) -> models.SimpleViewMixin:
        url = self.resource_url(uuid)
        resp = self._http_client.put(url, json=params)
        return self.__model__.restore_from_simple_view(**resp.json())

    def delete(self, uuid: sys_uuid.UUID) -> None:
        url = self.resource_url(uuid)
        self._http_client.delete(url)

    def do_action(
        self, name: str, uuid: sys_uuid.UUID, invoke: bool = False, **kwargs
    ) -> tp.Dict[str, tp.Any] | None:
        url = self.resource_url(uuid) + "/"
        action_url = urljoin(urljoin(url, self.ACTIONS_KEY) + "/", name)

        if invoke:
            action_url = urljoin(action_url + "/", self.INVOKE_KEY)
            resp = self._http_client.post(action_url, json=kwargs)
        else:
            resp = self._http_client.get(action_url, params=kwargs)

        # Try to convert response to json
        resp.raise_for_status()
        try:
            return resp.json()
        except bazooka_exc.BaseHTTPException:
            return None


class ResourceBaseModelClient(bazooka.Client):
    ACTIONS_KEY = "actions"
    INVOKE_KEY = "invoke"

    __model__: tp.Type[models.SimpleViewMixin] = None

    def __init__(
        self,
        collection: CollectionBaseModelClient,
        resource_uuid: sys_uuid.UUID,
        http_client: bazooka.Client | None = None,
    ):
        self._http_client = http_client or bazooka.Client()
        self._collection = collection
        self._resource_uuid = resource_uuid

    def resource_url(self):
        return self._collection.resource_url(self._resource_uuid)

    def get(self) -> models.SimpleViewMixin:
        url = self.resource_url()
        resp = self._http_client.get(url)
        return self.__model__.restore_from_simple_view(**resp.json())

    def update(self, **params: tp.Dict[str, tp.Any]) -> models.SimpleViewMixin:
        url = self.resource_url()
        resp = self._http_client.put(url, json=params)
        return self.__model__.restore_from_simple_view(**resp.json())

    def delete(self) -> None:
        url = self.resource_url()
        self._http_client.delete(url)

    def do_action(
        self, name: str, invoke: bool = False, **kwargs
    ) -> tp.Dict[str, tp.Any] | None:
        url = self.resource_url() + "/"
        action_url = urljoin(urljoin(url, self.ACTIONS_KEY) + "/", name)

        if invoke:
            action_url = urljoin(action_url + "/", self.INVOKE_KEY)
            resp = self._http_client.post(action_url, json=kwargs)
        else:
            resp = self._http_client.get(action_url, params=kwargs)

        # Try to convert response to json
        resp.raise_for_status()
        try:
            return resp.json()
        except bazooka_exc.BaseHTTPException:
            return None
