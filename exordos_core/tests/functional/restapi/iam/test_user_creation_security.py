import json
import sys
from unittest import mock
from urllib.parse import urljoin

from gcl_iam.tests.functional import clients as iam_clients
import pytest
import requests

from exordos_core.tests.functional.restapi.iam import base
from exordos_core.user_api.security.dm import models as security_models

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="altcha 0.2.x in security verifiers require Python 3.9+",
)

CREATE_USER_PATH = "iam/users/"


class TestUserCreationSecurity(base.BaseIamResourceTest):
    """Security rules for user creation: Firebase OR CAPTCHA OR admin bypass."""

    def _create_rule(
        self,
        name: str,
        verifier: security_models.AbstractVerifier,
        project_id=None,
    ) -> security_models.Rule:
        condition = security_models.UriRegexConditions(
            uri_regex=rf"^/v1/{CREATE_USER_PATH}$",
            method="POST",
        )
        rule = security_models.Rule(
            name=name,
            condition=condition,
            verifier=verifier,
            operator=security_models.OperatorEnum.OR.value,
            project_id=project_id,
        )
        rule.insert()
        return rule

    def _create_firebase_rule(
        self,
        project_id=None,
        allowed_app_ids=None,
    ):
        verifier = security_models.FirebaseAppCheckVerifier(
            credentials_path="/tmp/fake-firebase-credentials.json",
            allowed_app_ids=allowed_app_ids or [],
        )
        return self._create_rule(
            name="Firebase App Check for user creation",
            verifier=verifier,
            project_id=project_id,
        )

    def _create_captcha_rule(self, project_id=None):
        verifier = security_models.CaptchaVerifier(
            hmac_key="test-hmac-key-12345",
        )
        return self._create_rule(
            name="CAPTCHA for user creation",
            verifier=verifier,
            project_id=project_id,
        )

    def _create_admin_bypass_rule(
        self,
        allowed_identifiers,
        project_id=None,
    ):
        normalized = [str(v) for v in allowed_identifiers if v is not None]
        verifier = security_models.AdminBypassVerifier(
            bypass_users=normalized,
        )
        return self._create_rule(
            name="Admin bypass for user creation",
            verifier=verifier,
            project_id=project_id,
        )

    def _create_anonymous_bypass_rule(self, project_id=None):
        verifier = security_models.AnonymousBypassVerifier()
        return self._create_rule(
            name="Anonymous bypass for user creation",
            verifier=verifier,
            project_id=project_id,
        )

    def _user_create_url(self, user_api):
        return urljoin(user_api.base_url, CREATE_USER_PATH)

    def _post_create_user(self, user_api, headers, username_suffix="sec"):
        url = self._user_create_url(user_api)
        username = f"testuser_{username_suffix}"
        data = {
            "username": username,
            "password": "testpass123",
            "email": f"{username}@example.com",
        }
        return requests.post(url, json=data, headers=headers or {})

    @mock.patch("firebase_admin.app_check.verify_token")
    @mock.patch("firebase_admin.credentials.Certificate")
    @mock.patch("firebase_admin.initialize_app")
    @mock.patch("firebase_admin.get_app")
    def test_create_user_firebase_or_captcha_or_admin_bypass(
        self,
        mock_get_app,
        mock_initialize_app,
        mock_certificate,
        mock_verify_token,
        user_api,
        auth_user_admin,
        auth_test1_user,
    ):
        """Any of Firebase / CAPTCHA / admin-bypass should allow creation."""
        self._create_firebase_rule(allowed_app_ids=["test-app-id"])
        self._create_captcha_rule()
        self._create_admin_bypass_rule(
            allowed_identifiers=[
                auth_user_admin.email,
                str(auth_user_admin.uuid),
            ]
        )

        mock_get_app.side_effect = ValueError("No app")
        mock_initialize_app.return_value = mock.MagicMock()
        mock_certificate.return_value = mock.MagicMock()
        mock_verify_token.return_value = {"app_id": "test-app-id"}

        admin_token = self._get_access_token(user_api, auth_user_admin)

        headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-Firebase-AppCheck": "valid_firebase_token_12345",
        }
        response = self._post_create_user(user_api, headers, username_suffix="firebase")
        assert response.status_code in (200, 201)

        captcha_payload = json.dumps(
            {
                "challenge": "test_challenge_123",
                "number": 123456,
                "signature": "test_signature_123",
                "algorithm": "SHA-512",
                "salt": "test_salt?expires=9999999999",
            }
        )

        # altcha is imported inside verifier, so patch its global function
        with mock.patch("altcha.verify_solution") as mock_verify_solution:
            mock_verify_solution.return_value = (True, None)
            headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Captcha": captcha_payload,
            }
            response = self._post_create_user(
                user_api, headers, username_suffix="captcha"
            )
            assert response.status_code in (200, 201)

        headers = {
            "Authorization": f"Bearer {admin_token}",
        }
        with mock.patch(
            "exordos_core.user_api.security.dm.models.AdminBypassVerifier.verify",
            return_value=True,
        ):
            response = self._post_create_user(
                user_api, headers, username_suffix="admin_bypass"
            )
        assert response.status_code in (200, 201)

    def _get_access_token(self, user_api, auth):
        client = iam_clients.GenesisCoreTestRESTClient(
            f"{user_api.get_endpoint()}v1/",
            auth,
        )
        assert "access_token" in client._auth_cache
        return client._auth_cache["access_token"]

    def test_create_user_forbidden_when_no_rule_matches(
        self,
        user_api,
        auth_test1_user,
    ):
        """Без Firebase, CAPTCHA и без admin-bypass – должен быть 403 из SecurityRulesMiddleware."""
        self._create_firebase_rule(allowed_app_ids=["test-app-id"])
        self._create_captcha_rule()
        self._create_admin_bypass_rule(allowed_identifiers=["non-existent@example.com"])

        token = self._get_access_token(user_api, auth_test1_user)
        headers = {
            "Authorization": f"Bearer {token}",
        }

        response = self._post_create_user(
            user_api, headers, username_suffix="forbidden"
        )
        assert response.status_code == 403

    def test_anonymous_bypass_verifier_matches_all(
        self,
    ):
        """AnonymousBypassVerifier returns True for ALL requests."""
        from unittest import mock

        from gcl_iam import exceptions as gcl_iam_exceptions

        verifier = security_models.AnonymousBypassVerifier()

        # Test with NoIamSessionStored (no auth at all)
        ctx1 = mock.MagicMock()
        ctx1.iam_context.get_introspection_info.side_effect = (
            gcl_iam_exceptions.NoIamSessionStored()
        )
        assert verifier.verify(ctx1) is True

        # Test with anonymous token (type='anon')
        ctx2 = mock.MagicMock()
        info2 = mock.MagicMock()
        user_info2 = mock.MagicMock()
        user_info2.type = "anon"
        info2.user_info = user_info2
        ctx2.iam_context.get_introspection_info.return_value = info2
        assert verifier.verify(ctx2) is True

        # Test with authenticated user (type='user') - ALSO returns True now
        ctx3 = mock.MagicMock()
        info3 = mock.MagicMock()
        user_info3 = mock.MagicMock()
        user_info3.type = "user"
        info3.user_info = user_info3
        ctx3.iam_context.get_introspection_info.return_value = info3
        assert verifier.verify(ctx3) is True

    def test_anonymous_bypass_tracking_api(
        self,
    ):
        """Test anonymous bypass matched tracking API."""
        from exordos_core.common import contexts

        # Create mock request with environ
        mock_request = mock.MagicMock()
        mock_request.environ = {}

        # Create context with mock request
        ctx = mock.MagicMock(spec=contexts.GenesisCoreAuthContext)
        ctx.request = mock_request

        # Bind real methods to mock
        ctx.set_anonymous_bypass_matched = (
            contexts.GenesisCoreAuthContext.set_anonymous_bypass_matched.__get__(ctx)
        )
        ctx.is_anonymous_bypass_matched = (
            contexts.GenesisCoreAuthContext.is_anonymous_bypass_matched.__get__(ctx)
        )

        # Initially not matched
        assert ctx.is_anonymous_bypass_matched() is False

        # Set as matched
        ctx.set_anonymous_bypass_matched()

        # Now matched
        assert ctx.is_anonymous_bypass_matched() is True

    def test_create_user_anonymous_registration(
        self,
        user_api,
    ):
        """Anonymous user can register without authentication or permissions."""
        # Only anonymous bypass rule - no Firebase, no CAPTCHA needed
        self._create_anonymous_bypass_rule()

        # No Authorization header - completely anonymous request
        response = self._post_create_user(
            user_api, headers={}, username_suffix="street_user"
        )
        assert response.status_code in (200, 201), (
            f"Anonymous registration failed: {response.status_code} - {response.text[:200]}"
        )

        # Verify user was created
        data = response.json()
        assert "uuid" in data
        assert data["username"] == "testuser_street_user"

    def test_create_user_anonymous_without_rule_is_forbidden(
        self,
        user_api,
    ):
        """Anonymous user cannot register without AnonymousBypassVerifier Rule."""
        # No rules created at all - only default admin rules exist

        # No Authorization header - completely anonymous request
        response = self._post_create_user(
            user_api, headers={}, username_suffix="no_rule_user"
        )
        # Should be forbidden because no Rule allows anonymous access
        # AND user doesn't have iam.user.create permission
        assert response.status_code == 403

    def test_authenticated_user_with_anonymous_bypass_rule(
        self,
        user_api,
        auth_test1_user,
    ):
        """Authenticated user CAN register when AnonymousBypassVerifier Rule exists.

        The Rule allows "street" registration for any request, regardless
        of whether the user is anonymous or authenticated.
        """
        self._create_anonymous_bypass_rule()

        token = self._get_access_token(user_api, auth_test1_user)
        headers = {"Authorization": f"Bearer {token}"}

        # Authenticated request with AnonymousBypassVerifier Rule
        response = self._post_create_user(
            user_api, headers=headers, username_suffix="auth_with_rule"
        )
        # Should succeed because Rule allows registration without permission
        assert response.status_code in (200, 201), (
            f"Auth user with Rule failed: {response.status_code} - {response.text[:200]}"
        )
