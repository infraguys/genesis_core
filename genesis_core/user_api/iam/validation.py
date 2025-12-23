from typing import Iterable

from webob import Request

from genesis_core.user_api.iam import exceptions as iam_exceptions
from genesis_core.user_api.iam.dm import models as iam_models


class ClientRequestValidator:
    """Applies IamClient validation rules to a request."""

    def validate(self, client: iam_models.IamClient, request: Request) -> None:
        """Applies validation rules, first matching rule validates the request."""
        rules: Iterable = client.get_validation_rules()
        if not rules:
            return

        for rule in rules:
            if rule.verifier.can_handle(request):
                rule.verify(request)
                return

        raise iam_exceptions.CanNotCreateUser(message="No matching validation found")
