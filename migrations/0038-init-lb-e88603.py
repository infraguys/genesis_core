#    Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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

from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = ["0037-manifest-indexes-815825.py"]

    @property
    def migration_id(self):
        return "e8860362-cba3-4fa9-b6ec-9395ddec13c3"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """\
CREATE TABLE net_lb (
    uuid UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    project_id UUID NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'NEW',
    "ipsv4" varchar(15) ARRAY,
    type JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX ON net_lb(project_id, name);
""",
            """\
CREATE TABLE net_lb_vhosts (
    uuid UUID PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(64) NOT NULL DEFAULT 'NEW',
    description TEXT,
    project_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    protocol VARCHAR(10) NOT NULL,
    port INT NOT NULL,
    domains VARCHAR(255) ARRAY,
    cert JSONB,
    parent UUID NOT NULL,
    FOREIGN KEY (parent) REFERENCES net_lb(uuid)
);

CREATE INDEX ON net_lb_vhosts(project_id);
CREATE INDEX ON net_lb_vhosts(parent, name);
CREATE INDEX ON net_lb_vhosts(parent, port, domains);
""",
            """\
CREATE TABLE net_lb_vhosts_routes (
    uuid UUID PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(64) NOT NULL DEFAULT 'NEW',
    description TEXT,
    project_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    condition JSONB,
    parent UUID NOT NULL,
    FOREIGN KEY (parent) REFERENCES net_lb_vhosts(uuid)
);

CREATE INDEX ON net_lb_vhosts_routes(project_id);
CREATE INDEX ON net_lb_vhosts_routes(parent, name);
""",
            """\
CREATE TABLE net_lb_backendpools (
    uuid UUID PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'NEW',
    description TEXT,
    project_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    endpoints JSONB[] NOT NULL,
    balance VARCHAR(32) NOT NULL,
    parent UUID NOT NULL,
    FOREIGN KEY (parent) REFERENCES net_lb(uuid)
);

CREATE INDEX ON net_lb_backendpools(project_id);
CREATE INDEX ON net_lb_backendpools(parent, name);
""",
        ]

        for expression in expressions:
            session.execute(expression, None)

    def downgrade(self, session):

        tables = [
            "net_lb_backendpools",
            "net_lb_vhosts_routes",
            "net_lb_vhosts",
            "net_lb",
        ]

        for table in tables:
            self._delete_table_if_exists(session, table)


migration_step = MigrationStep()
