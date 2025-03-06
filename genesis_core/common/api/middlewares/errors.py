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

from http import client as http_client

from gcl_iam import middlewares
from restalchemy.api import middlewares as errors_mw

from genesis_core.common import exceptions as common_exc


class ErrorsHandlerMiddleware(middlewares.ErrorsHandlerMiddleware):

    not_found_exc = middlewares.ErrorsHandlerMiddleware.not_found_exc + (
        common_exc.CommonNotFoundException,
    )
    forbidden_exc = (common_exc.CommonForbiddenException,)

    def _construct_error_response(self, req, e):
        if isinstance(e, self.forbidden_exc):
            return req.ResponseClass(
                status=http_client.FORBIDDEN, json=errors_mw.exception2dict(e)
            )
        else:
            return super()._construct_error_response(req, e)
