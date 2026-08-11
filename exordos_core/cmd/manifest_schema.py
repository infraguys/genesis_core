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

"""Rewrite the manifest schema installations validate against.

`full_spec.yaml` is derived from the user API: every path that creates
something becomes a resource type a manifest may declare, carrying the
schema of its create body. Unlike the other generated artefacts it is
committed, because it ships in the package and is read while the platform
runs -- so this writes it where the package reads it, and `git diff` is
how you see what changed.

Run it after changing anything the user API creates;
`test_full_spec_is_current` stays red until you do.
"""

import argparse
import sys

from exordos_core.elements.dm import utils


def main() -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()

    schema = utils.build_full_schema(
        utils.load_base_manifest_schema(), utils.load_user_api_spec()
    )
    utils.dump_full_manifest_schema(schema)

    resource_types = schema["properties"]["resources"]["properties"]
    print(
        f"full_spec.yaml: {len(resource_types)} resource types, "
        f"{len(schema['components']['schemas'])} schemas"
    )


if __name__ == "__main__":
    sys.exit(main())
