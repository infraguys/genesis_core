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


from gcl_iam import controllers as iam_controllers
from restalchemy.dm import filters as dm_filters
from restalchemy.api import actions
from restalchemy.api import controllers
from restalchemy.api import resources
from restalchemy.common import exceptions as ra_e

from genesis_core.elements.dm import models
from genesis_core.vs.dm import models as vs_models


class ElementHasNoProfileError(ra_e.ValidationErrorException):
    message = "Element has no profile"


class ElementManagerController(controllers.RoutesListController):
    __TARGET_PATH__ = "/v1/em/"


class ManifestController(
    iam_controllers.PolicyBasedWithoutProjectController,
    controllers.BaseResourceControllerPaginated,
):
    __policy_service_name__ = "em"
    __policy_name__ = "manifest"
    __resource__ = resources.ResourceByRAModel(
        model_class=models.Manifest,
        convert_underscore=False,
        hidden_fields=resources.HiddenFieldMap(
            update=["status", "created_at", "updated_at"],
        ),
    )

    @actions.post
    def install(self, resource):
        return resource.install()

    @actions.post
    def upgrade(self, resource):
        return resource.upgrade()

    @actions.post
    def uninstall(self, resource):
        return resource.uninstall()


class ElementController(
    iam_controllers.PolicyBasedWithoutProjectController,
    controllers.BaseResourceControllerPaginated,
):
    __policy_service_name__ = "em"
    __policy_name__ = "element"
    __resource__ = resources.ResourceByModelWithCustomProps(
        model_class=models.Element,
        convert_underscore=False,
        hidden_fields=resources.HiddenFieldMap(
            update=[
                "status",
                "created_at",
                "updated_at",
                "name",
                "version",
            ],
        ),
    )

    @actions.post
    def set_profile(self, resource: models.Element, profile: str):
        profile = vs_models.Profile.objects.get_one(
            filters={"uuid": dm_filters.EQ(profile)},
        )
        resource.profile = profile
        resource.update()

        # Need to update force to rebuild the variables
        # related to the profile
        profile.update(force=True)
        return resource

    @actions.post
    def clear_profile(self, resource: models.Element):
        if not resource.profile:
            raise ElementHasNoProfileError()

        profile = resource.profile
        resource.profile = None
        resource.update()

        # Need to update force to rebuild the variables
        # related to the profile
        profile.update(force=True)
        return resource


class ElementResourceController(
    # iam_controllers.PolicyBasedWithoutProjectController,  # nested
    controllers.BaseNestedResourceControllerPaginated,
):
    __pr_name__ = "element"
    # __policy_service_name__ = "em"
    # __policy_name__ = "resource"
    __resource__ = resources.ResourceByModelWithCustomProps(
        model_class=models.Resource,
        convert_underscore=False,
        hidden_fields=resources.HiddenFieldMap(
            filter=[
                "target_resource",
                "actual_resource",
            ],
            get=[
                "target_resource",
                "actual_resource",
            ],
            create=[
                "target_resource",
                "actual_resource",
            ],
            update=[
                "target_resource",
                "actual_resource",
                "status",
                "created_at",
                "updated_at",
                "name",
                "version",
            ],
        ),
    )


class ServicesController(iam_controllers.PolicyBasedController):
    """Controller for /v1/em/services/ endpoint"""

    __policy_name__ = "em"
    __policy_service_name__ = "service"

    __resource__ = resources.ResourceByRAModel(
        model_class=models.Service,
        process_filters=True,
        convert_underscore=False,
    )
