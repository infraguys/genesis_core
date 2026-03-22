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

import os
import dataclasses
import socket
import contextlib
import pathlib
from urllib import parse
import typing as tp
from types import TracebackType

from gcl_sdk import migrations as sdk_migrations
from restalchemy.storage.sql import migrations, engines
from restalchemy.tests.functional import db_utils as ra_db_utils, consts as ra_consts
from restalchemy.tests.functional.restapi.ra_based.microservice import service

from unittest.mock import patch

ENDPOINT_TEMPLATE = "http://127.0.0.1:%s/"


class RestServiceTestCase(ra_db_utils.DBEngineMixin):
    __LAST_MIGRATION__ = None
    __FIRST_MIGRATION__ = None
    __API_VERSION__ = "v1"
    __APP__ = None

    @classmethod
    def get_endpoint(cls, template: str = ENDPOINT_TEMPLATE) -> str:
        return template % cls.service_port

    @classmethod
    def find_free_port(cls) -> int:
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(("127.0.0.1", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]


    @classmethod
    def setup_class(cls):
        cls.init_engine()
        # Run service
        cls.service_port = cls.find_free_port()
        url = parse.urlparse(cls.get_endpoint())
        cls._service = service.RESTService(
            bind_host=url.hostname, bind_port=url.port, app_root=cls.__APP__
        )
        cls._service.start()

    @classmethod
    def teardown_class(cls):
        cls._service.stop()
        cls.drop_all_views()
        cls.drop_all_tables(cascade=True)
        # Hack for psycopg to finish fast, otherwise we'll need to wait for GC
        cls.engine.__del__()
        cls.destroy_engine()

    @staticmethod
    def get_migration_engine(
        migrations_path: tp.Optional[str] = None,
    ) -> migrations.MigrationEngine:
        if migrations_path is None:
            migrations_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "../../../migrations",
            )

        migration_engine = migrations.MigrationEngine(migrations_path=migrations_path)
        return migration_engine

    @classmethod
    def apply_migrations(
        cls,
        migration_path: str,
        first_migration: str,
        last_migration: tp.Optional[str] = None,
    ) -> migrations.MigrationEngine:

        migration_engine = cls.get_migration_engine(migrations_path=migration_path)
        migration_engine.rollback_migration(first_migration)

        last_migration = last_migration or migration_engine.get_latest_migration()
        migration_engine.apply_migration(last_migration)
        return migration_engine

    def apply_all_migrations(self) -> None:
        self._sdk_migration = self.apply_migrations(
            migration_path=str(pathlib.Path(sdk_migrations.__file__).parent),
            first_migration=sdk_migrations.INIT_MIGRATION_FILENAME,
            last_migration=None,
            )
        self._migration = self.apply_migrations(
            migration_path=os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "../../../migrations",
            ),
            first_migration=self.__FIRST_MIGRATION__,
            last_migration=self.__LAST_MIGRATION__,
        )

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
    def get_all_views(cls, session=None) -> tp.Set[str]:
        with cls.engine.session_manager(session=session) as s:
            if session.engine.dialect.name == "mysql":
                res = s.execute("""
                    select
                        table_name as table_name
                    from information_schema.views
                    where table_schema = database();
                """).fetchall()
            elif session.engine.dialect.name == "postgresql":
                res = s.execute("""
                    select
                        table_name as table_name
                    from information_schema.views
                    where table_schema = current_schema();
                """).fetchall()
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
            s.execute(f"drop view if exists {session.engine.escape(view_name)}")

    def setup_method(self) -> None:
        # Apply migrations
        self.apply_all_migrations()

    def teardown_method(self) -> None:
        # Rollback migrations
        self._migration.rollback_migration(self.__FIRST_MIGRATION__)
        self._sdk_migration.rollback_migration(sdk_migrations.INIT_MIGRATION_FILENAME)


@contextlib.contextmanager
def patch_engines_default(
    db_manager: "TestDBManager",
) -> tp.Iterable[None]:
    default_name = engines.DEFAULT_NAME
    default_get_engine = engines.EngineFactory.get_engine

    def _patched_get_engine(
        factory: engines.EngineFactory,
        name: str = default_name,
    ) -> engines.AbstractEngine:
        if name == default_name:
            return db_manager.engine
        else:
            return default_get_engine(factory, name=name)

    with \
        patch(
            "restalchemy.storage.sql.engines.DEFAULT_NAME",
            db_manager.manager_config.engine_alias,
        ), \
        patch.object(
            engines.EngineFactory,
            "get_engine",
            _patched_get_engine,
        ):
            yield


OptionalStr = tp.Optional[str]


class AbstractCursor(tp.Protocol):
    def execute(self, statement: str) -> tp.Any:
        ...


class AbstractConnection(tp.Protocol):
    autocommit: bool

    @contextlib.contextmanager
    def cursor(self) -> tp.Iterable[AbstractCursor]:
        ...

    def rollback(self) -> None:
        ...


class AbstractSession(tp.Protocol):
    def execute(self, statement, values=None) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def close(self) -> None:
        ...


@dataclasses.dataclass()
class TestDBManagerConfig:
    database_url: OptionalStr = None
    engine_alias: OptionalStr = None
    create_db: OptionalStr = None

    def __post_init__(self) -> None:
        self.database_url = self.database_url or ra_consts.get_database_uri()
        self.engine_alias = self.engine_alias or engines.DEFAULT_NAME


class TestDBManager:
    _Self = tp.TypeVar("_Self", bound="TestDBManager")

    manager_config: tp.ClassVar[TestDBManagerConfig] = TestDBManagerConfig()

    _engine: engines.AbstractEngine

    @property
    def engine(self) -> engines.AbstractEngine:
        return self._engine

    def setup(self) -> _Self:
        engine_alias = self.manager_config.engine_alias

        engines.engine_factory.configure_factory(
            db_url=self.manager_config.database_url,
            name=engine_alias,
        )
        self._engine = engines.engine_factory.get_engine(engine_alias)

        return self

    def teardown(self) -> None:
        if isinstance(self._engine, engines.PgSQLEngine):
            self._engine._pool.close()

        engines.engine_factory.destroy_engine(
            name=self.manager_config.engine_alias,
        )

    def __enter__(self) -> _Self:
        return self.setup()

    def __exit__(
        self,
        exc_type: tp.Type[Exception],
        exc_val: Exception,
        exc_tb: TracebackType
    ) -> None:
        self.teardown()

    @contextlib.contextmanager
    def session(self) -> tp.Iterable[AbstractSession]:
        session: AbstractSession = self._engine.get_session()

        try:
            with patch_engines_default(db_manager=self):
                yield session
        finally:
            session.rollback()
            session.close()

    @contextlib.contextmanager
    def connection(
        self,
        autocommit: bool = False,
    ) -> tp.Iterable[AbstractConnection]:
        connection: AbstractConnection = self._engine.get_connection()

        try:
            connection.autocommit = autocommit
            yield connection
        finally:
            if not autocommit:
                connection.rollback()

            self._engine.close_connection(connection)

    def create_db(self) -> None:
        create_db = self.manager_config.create_db
        if create_db is None:
            return

        with self.connection(autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE \"{create_db}\"")

    def drop_db(self) -> None:
        create_db = self.manager_config.create_db
        if create_db is None:
            return

        with self.connection(autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE \"{create_db}\"")
    @contextlib.contextmanager
    def db(self) -> tp.Iterable[_Self]:
        try:
            self.create_db()
            yield self

        finally:
            self.drop_db()


@dataclasses.dataclass()
class TestMigrationManagerConfig:
    migrations_path: OptionalStr = None
    first_migration: OptionalStr = None
    last_migration: OptionalStr = None

    def __post_init__(self) -> None:
        self.migrations_path = (
            self.migrations_path
            or (
                str(
                    pathlib.Path(__file__)
                    .parent
                    .joinpath("../../../migrations/")
                    .resolve()
                )
            )
        )


class TestMigrationManager:
    _Self = tp.TypeVar("_Self", bound="TestMigrationManager")

    migration_config: tp.ClassVar[
        TestMigrationManagerConfig
    ] = TestMigrationManagerConfig()

    _migration_engine: migrations.MigrationEngine

    def __init__(
        self,
        db_manager: TestDBManager,
    ) -> None:
        self._db_manager = db_manager

    @property
    def db_manager(self) -> TestDBManager:
        return self._db_manager

    def setup(self) -> _Self:
        self._migration_engine = migrations.MigrationEngine(
            migrations_path=self.migration_config.migrations_path,
        )

        return self

    def __enter__(self) -> _Self:
        return self.setup()

    def __exit__(
        self,
        exc_type: tp.Type[Exception],
        exc_val: Exception,
        exc_tb: TracebackType,
    ) -> None:
        return

    def apply_migrations(self) -> _Self:
        last_migration = (
            self.migration_config.last_migration
            or self._migration_engine.get_latest_migration()
        )

        with patch_engines_default(
            db_manager=self.db_manager,
        ):
            self._migration_engine.apply_migration(
                migration_name=last_migration,
            )

        return self

    def rollback_migrations(self) -> None:
        with patch_engines_default(
            db_manager=self.db_manager,
        ):
            self._migration_engine.rollback_migration(
                migration_name=self.migration_config.first_migration,
            )

    @contextlib.contextmanager
    def migrations(self) -> tp.Iterable[_Self]:
        try:
            yield self.apply_migrations()
        finally:
            self.rollback_migrations()