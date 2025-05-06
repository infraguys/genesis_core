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

from restalchemy.dm import models


class ModelWithFullAsset(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
    models.ModelWithProject,
    models.ModelWithNameDesc,
):
    pass


class CastToBaseMixin:
    __cast_fields__ = None

    def cast_to_base(self) -> models.SimpleViewMixin:
        # Convert to simple view without relations
        fields = self.__cast_fields__ or tuple(
            self.properties.properties.keys()
        )
        view = self.dump_to_simple_view(skip=fields)

        # Translate relations into uuid
        for relation in fields:
            value = getattr(self, relation)
            if value is not None:
                view[relation] = value.uuid

        # Find base class
        base_class = None
        for base in self.__class__.__bases__:
            if base != CastToBaseMixin:
                base_class = base
                break
        else:
            raise RuntimeError(
                f"Failed to find base class for {self.__class__}"
            )

        return base_class.restore_from_simple_view(**view)
