#    Copyright 2026 Genesis Corporation.
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

"""`full_spec.yaml` is committed, so it can go stale. This says when.

It stays in the tree, unlike the OpenAPI documents, because it ships in
the package and a running installation validates every manifest against
it. Nothing compared it with the API it is derived from, and it had
drifted: it offered `$core.iam.organization_members`, a resource type no
endpoint has ever served, so a manifest declaring it passed validation and
failed at apply.

To make this pass after an API change, regenerate the schema with
`test_build_full_schema` in `tests/functional/manifests/test_validate.py`.
"""

import yaml

from exordos_core.elements.dm import utils


def test_full_spec_matches_the_api_it_is_derived_from():
    built = utils.build_full_schema(
        utils.load_base_manifest_schema(), utils.load_user_api_spec()
    )
    # The committed copy has been through a YAML round trip and this one
    # has not, which is a difference in types rather than in content.
    built = yaml.safe_load(yaml.safe_dump(built))
    committed = utils.load_full_manifest_schema()

    # Spelled out before comparing the documents, because a whole-schema
    # mismatch says nothing about what moved.
    assert set(built["properties"]["resources"]["properties"]) == set(
        committed["properties"]["resources"]["properties"]
    )
    assert set(built["components"]["schemas"]) == set(
        committed["components"]["schemas"]
    )
    assert built == committed
