import logging
import typing as tp
from datetime import datetime, timezone

from gcl_looper.services import basic
from restalchemy.common import contexts
from restalchemy.dm import filters as dm_filters

from genesis_core.common import constants as c
from genesis_core.user_api.iam import constants as iam_c
from genesis_core.user_api.iam.dm import models

LOG = logging.getLogger(__name__)


class ExpiredEmailConfirmationCodeJanitorService(basic.BasicService):
    """
    Cleans up expired email confirmation codes from Users table.
    """

    def __init__(
        self,
        limit: int = c.DEFAULT_SQL_LIMIT,
        *args: tp.Any,
        **kwargs: tp.Any,
    ) -> None:
        self._limit = limit
        super().__init__(*args, **kwargs)

    def _clean_bad_confirmation_codes(self) -> None:
        now = datetime.now(tz=timezone.utc)
        expiration_time = now - iam_c.USER_CONFIRMATION_CODE_TTL
        LOG.debug("Starting to clean codes older than %s", expiration_time)
        filters = dm_filters.AND(
            dm_filters.OR(
                # actually expired codes:
                dm_filters.AND(
                    {"confirmation_code_made_at": dm_filters.LT(expiration_time)}
                ),
                # self-heal codes without timestamps:
                dm_filters.AND(
                    {
                        "confirmation_code_made_at": dm_filters.Is(None),
                        "confirmation_code": dm_filters.IsNot(None),
                    }
                ),
            )
        )
        users = models.User.objects.get_all(
            filters=filters,
            limit=self._limit,
            order_by={"confirmation_code_made_at": "asc"},
        )
        for user in users:
            user.clear_confirmation_code()

        LOG.debug("Users cleaned: %s" % len(users))

    def _iteration(self) -> None:
        with contexts.Context().session_manager():
            self._clean_bad_confirmation_codes()
