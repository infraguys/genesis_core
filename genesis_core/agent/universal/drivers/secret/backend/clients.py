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
import uuid as sys_uuid
import typing as tp

from gcl_iam.tests.functional import clients as iam_clients


class TinyDNSCoreClient(iam_clients.GenesisCoreTestRESTClient):

    # def list_domains(self) -> list[dict[str, tp.Any]]:
    #     url = self.build_collection_uri(("dns", "domains"))
    #     return self.get(url=url).json()

    # def list_records(self, domain: sys_uuid.UUID) -> list[dict[str, tp.Any]]:
    #     url = self.build_collection_uri(
    #         ("dns", "domains", str(domain), "records")
    #     )
    #     return self.get(url=url).json()

    def create_txt_record(
        self, domain: str, name: str, content: str
    ) -> dict[str, tp.Any]:
        url = self.build_collection_uri(("dns", "domains"))
        parent_domain = domain

        # Try to find target zone iteratively.
        while parent_domain:
            try:
                parent_domain = parent_domain.split(".", 1)[1]
            except IndexError:
                raise ValueError(
                    f"Could not find DNS zone for domain {domain}"
                )

            response = self.get(url, params={"name": parent_domain}).json()
            if response:
                zone = response[0]
                break

        data = {
            "type": "TXT",
            "ttl": 0,
            "record": {
                "kind": "TXT",
                "name": name,
                "content": content,
            },
        }

        url = self.build_collection_uri(
            ("dns", "domains", zone["uuid"], "records")
        )

        return self.post(url, json=data).json()

    def delete_record(self, domain: sys_uuid.UUID, record: sys_uuid.UUID):
        url = self.build_resource_uri(
            ("dns", "domains", str(domain), "records", str(record))
        )
        return self.delete(url)
