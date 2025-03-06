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

import os
import socket
import contextlib
from urllib import parse

from restalchemy.storage.sql import migrations
from restalchemy.tests.functional import db_utils as ra_db_utils
from restalchemy.tests.functional.restapi.ra_based.microservice import service


ENDPOINT_TEMPLATE = "http://127.0.0.1:%s/"


class RestServiceTestCase(ra_db_utils.DBEngineMixin):
    __LAST_MIGRATION__ = None
    __FIRST_MIGRATION__ = None
    __API_VERSION__ = "v1"
    __APP__ = None

    @classmethod
    def setup_class(cls):
        cls.init_engine()

    @classmethod
    def teardown_class(cls):
        cls.drop_all_views()
        cls.drop_all_tables(cascade=True)
        cls.destroy_engine()

    @staticmethod
    def get_migration_engine(migrations_path: str | None = None) -> None:
        if migrations_path is None:
            migrations_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "../../../migrations",
            )

        migration_engine = migrations.MigrationEngine(
            migrations_path=migrations_path
        )
        return migration_engine

    @property
    def base_url(self) -> str:
        return self.get_endpoint() + self.__API_VERSION__ + "/"

    @classmethod
    def drop_table(cls, table_name, session=None, cascade=False):
        cascade = " CASCADE" if cascade else ""
        with cls.engine.session_manager(session=session) as s:
            s.execute(
                f"drop table if exists {session.engine.escape(table_name)}{cascade}"
            )

    @classmethod
    def drop_all_tables(cls, session=None, cascade=False):
        with cls.engine.session_manager(session=session) as s:
            tables = cls.get_all_tables(session=s)
            for table in tables:
                cls.drop_table(table, session=s, cascade=cascade)

    @classmethod
    def get_all_views(cls, session=None) -> set[str]:
        with cls.engine.session_manager(session=session) as s:
            if session.engine.dialect.name == "mysql":
                res = s.execute(
                    """
                    select
                        table_name as table_name
                    from information_schema.views
                    where table_schema = database();
                """
                ).fetchall()
            elif session.engine.dialect.name == "postgresql":
                res = s.execute(
                    """
                    select
                        table_name as table_name
                    from information_schema.views
                    where table_schema = current_schema();
                """
                ).fetchall()
            else:
                raise NotImplementedError("Unsupported dialect")
        return {row["table_name"] for row in res}

    @classmethod
    def drop_all_views(cls, session=None):
        with cls.engine.session_manager(session=session) as s:
            views = cls.get_all_views(session=s)
            for view in views:
                cls.drop_view(view, session=s)

    @classmethod
    def drop_view(cls, view_name, session=None):
        with cls.engine.session_manager(session=session) as s:
            s.execute(
                f"drop view if exists {session.engine.escape(view_name)}"
            )

    def get_endpoint(self, template: str = ENDPOINT_TEMPLATE) -> str:
        return template % self.service_port

    def find_free_port(self) -> int:
        with contextlib.closing(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ) as s:
            s.bind(("127.0.0.1", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    def setup_method(self) -> None:
        # Apply migrations
        self._migrations = self.get_migration_engine()
        self._migrations.rollback_migration(self.__FIRST_MIGRATION__)
        self._migrations.apply_migration(self.__LAST_MIGRATION__)

        # Run service
        self.service_port = self.find_free_port()
        url = parse.urlparse(self.get_endpoint())
        self._service = service.RESTService(
            bind_host=url.hostname, bind_port=url.port, app_root=self.__APP__
        )
        self._service.start()

    def teardown_method(self) -> None:
        self._service.stop()

        # Rollback migrations
        self._migrations = self.get_migration_engine()
        self._migrations.rollback_migration(self.__FIRST_MIGRATION__)
