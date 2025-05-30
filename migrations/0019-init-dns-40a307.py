# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
# Copyright 2025 Genesis Corporation
#
# All Rights Reserved.
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

from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = ["0018-add-elements-76bca4.py"]

    @property
    def migration_id(self):
        return "40a307b3-fdcc-46d8-bc81-1e2a53ac59e4"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
CREATE SEQUENCE dns_domain_id_seq;
            """,
            """
CREATE TABLE dns_domains (
    uuid                  UUID PRIMARY KEY,
    id                    INT UNIQUE DEFAULT nextval('dns_domain_id_seq'),
    name                  VARCHAR(255) NOT NULL,
    master                VARCHAR(128) DEFAULT NULL,
    last_check            INT DEFAULT NULL,
    type                  TEXT NOT NULL DEFAULT 'NATIVE',
    notified_serial       BIGINT DEFAULT NULL,
    account               VARCHAR(40) DEFAULT NULL,
    options               TEXT DEFAULT NULL,
    catalog               TEXT DEFAULT NULL,
    CONSTRAINT c_lowercase_name CHECK (((name)::TEXT = LOWER((name)::TEXT))),
    -- our (plus uuid)
    project_id            UUID NOT NULL,
    "created_at"          TIMESTAMP(6) NOT NULL DEFAULT NOW(),
    "updated_at"          TIMESTAMP(6) NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX ON dns_domains(id);
CREATE UNIQUE INDEX ON dns_domains(name);
CREATE INDEX ON dns_domains(catalog);
CREATE INDEX on dns_domains(project_id, name);
            """,
            """
CREATE TABLE dns_domainmetadata (
    id                    SERIAL PRIMARY KEY,
    domain_id             INT REFERENCES dns_domains(id) ON DELETE CASCADE,
    kind                  VARCHAR(32),
    content               TEXT
);

CREATE INDEX ON dns_domainmetadata(domain_id);
            """,
            """
CREATE TABLE dns_records (
    uuid                  UUID PRIMARY KEY,
    domain_id             INT DEFAULT NULL REFERENCES dns_domains(id) ON DELETE RESTRICT,
    name                  VARCHAR(255) DEFAULT NULL CHECK (((name)::TEXT = LOWER((name)::TEXT))),
    type                  VARCHAR(10) DEFAULT NULL,
    content               VARCHAR(65535) DEFAULT NULL,
    ttl                   INT DEFAULT NULL,
    prio                  INT DEFAULT NULL,
    disabled              BOOL DEFAULT 'f',
    ordername             VARCHAR(255),
    auth                  BOOL DEFAULT 't',
    -- our (plus uuid)
    domain                UUID NOT NULL REFERENCES dns_domains(uuid) ON DELETE CASCADE,
    "record"              JSONB NOT NULL,
    "created_at"          TIMESTAMP(6) NOT NULL DEFAULT NOW(),
    "updated_at"          TIMESTAMP(6) NOT NULL DEFAULT NOW()
);

CREATE INDEX rec_name_index ON dns_records(name);
CREATE INDEX nametype_index ON dns_records(name,type);
CREATE INDEX domain_id ON dns_records(domain_id);
CREATE INDEX recordorder ON dns_records (domain_id, ordername text_pattern_ops);
            """,
            """
CREATE VIEW domains AS
SELECT id, name, master, last_check, type, notified_serial, account, options, catalog FROM dns_domains;
            """,
            """
CREATE VIEW records AS
SELECT domain_id, name, type, content, ttl, prio, disabled, ordername, auth FROM dns_records;
            """,
            """
CREATE VIEW domainmetadata AS
SELECT id, domain_id, kind, content FROM dns_domainmetadata;
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        views = [
            "domains",
            "records",
            "domainmetadata",
        ]

        tables = [
            "dns_records",
            "dns_domainmetadata",
            "dns_domains",
        ]

        for view in views:
            self._delete_view_if_exists(session, view)

        for table in tables:
            self._delete_table_if_exists(session, table)

        session.execute("DROP SEQUENCE IF EXISTS dns_domain_id_seq;")


migration_step = MigrationStep()
