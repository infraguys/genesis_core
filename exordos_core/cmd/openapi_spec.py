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

"""Write the OpenAPI documents the site publishes.

Run before building the documentation; the pages under `docs/openapi` load
these files, and nothing else reads them.
"""

import argparse
import os
import sys

import ruamel.yaml

from exordos_core.common import openapi

# Relative to the working directory rather than to the installed package:
# this writes into a checkout, and the package it imports may well be
# installed somewhere else.
DEFAULT_OUTPUT_DIR = os.path.join("docs", "openapi")


def _yaml() -> ruamel.yaml.YAML:
    dumper = ruamel.yaml.YAML()
    dumper.indent(sequence=4, offset=2)
    return dumper


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "-o",
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"where to write the documents (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--openapi-version",
        default=openapi.OPENAPI_VERSION,
        help=f"OpenAPI version to emit (default: {openapi.OPENAPI_VERSION})",
    )
    args = parser.parse_args()

    dumper = _yaml()
    os.makedirs(args.output_dir, exist_ok=True)
    for api, specification in openapi.build_all(version=args.openapi_version).items():
        path = os.path.join(args.output_dir, api.filename)
        with open(path, "w") as f:
            dumper.dump(specification, f)
        print(f"{path}: {len(specification['paths'])} paths")


if __name__ == "__main__":
    sys.exit(main())
