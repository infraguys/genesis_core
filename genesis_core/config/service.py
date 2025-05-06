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

import logging
import datetime
import itertools
import collections
import typing as tp

from restalchemy.common import contexts
from restalchemy.dm import filters as dm_filters
from restalchemy.storage import exceptions as ra_exceptions
from gcl_looper.services import basic

from genesis_core.node.dm import models as node_models
from genesis_core.config.dm import models
from genesis_core.config import constants as cc


LOG = logging.getLogger(__name__)
ORPHAN_CFG_ITERATION_FREQUENCY = 10
DEF_OUTDATE_MIN_PERIOD = datetime.timedelta(minutes=10)


class ConfigService(basic.BasicService):

    def _get_configs(
        self,
        statuses: tp.Iterable[cc.ConfigStatus],
        limit: int = cc.DEFAULT_SQL_LIMIT,
    ) -> tp.DefaultDict[cc.ConfigStatus, tp.List[models.Config]]:
        """Returns all by status."""
        if len(statuses) == 0:
            return collections.defaultdict(list)

        configs = models.Config.objects.get_all(
            filters={
                "status": dm_filters.In(status.value for status in statuses),
            },
            limit=limit,
        )
        config_map = collections.defaultdict(list)
        for config in configs:
            config_map[cc.ConfigStatus[config.status]].append(config)

        return config_map

    def _get_renders(
        self, configs: tp.Collection[models.Config]
    ) -> tp.DefaultDict[models.Config, tp.List[models.Render]]:
        renders = models.Render.objects.get_all(
            filters={
                "config": dm_filters.In(configs),
            }
        )

        render_map = collections.defaultdict(list)
        for render in renders:
            render_map[render.config].append(render)

        return render_map

    def _actualize_new_config(
        self,
        config: models.Config,
        target_nodes: tp.List[node_models.Node],
    ) -> None:
        # Validate the owners exist
        # FIXME(akremenetsky): Only nodes as owners are supported for now.
        # It will be update when sets will appear.

        # FIXME(akremenetsky): Seems the config may be deleted since its
        # owners are absent. May be it will be better to control this
        # behavior via an additional option in the target model but for
        # now just delete this config.
        if not config.target.are_owners_alive():
            LOG.error("Config %s has no owners, delete it.", config.uuid)
            config.delete()
            return

        # FIXME(akremenetsky): Should we set status `IN_PROGRESS` here?
        # Let's wait at least one node to be created
        if len(target_nodes) == 0:
            return

        # Make renders for this config
        for node in target_nodes:
            render = config.render(node=node.uuid)

            # It's possible that the render already exists so just skip it
            try:
                render.insert()
                LOG.debug("Render %s created", render.uuid)
            except ra_exceptions.ConflictRecords:
                LOG.warning("Render %s already exists", render.uuid)

        config.status = cc.ConfigStatus.IN_PROGRESS.value
        config.save()

    def _actualize_new_configs(self, configs: tp.List[models.Config]) -> None:
        if len(configs) == 0:
            return

        # Remove all outdate renders for these configs
        renders = self._get_renders(configs)
        for render in itertools.chain.from_iterable(renders.values()):
            # It's ok if this operation fails. Make the code simple and
            # don't handle this failure, just try next iteration.
            render.delete()
            LOG.debug("Outdated render %s deleted", render.uuid)

        # Collect all target nodes
        target_nodes = set()
        for config in configs:
            target_nodes |= {n for n in config.target_nodes()}

        nodes = {
            n.uuid: n
            for n in node_models.Node.objects.get_all(
                filters={
                    "uuid": dm_filters.In(str(u) for u in target_nodes),
                }
            )
        }

        # Make renders for each new config
        for config in configs:
            # Collect all available nodes for the config
            target_nodes = tuple(
                nodes[n] for n in config.target_nodes() if n in nodes
            )
            try:
                self._actualize_new_config(config, target_nodes)
            except Exception:
                LOG.exception("Error actualizing config %s", config.uuid)

    def _actualize_in_progress_configs(
        self, configs: tp.List[models.Config]
    ) -> None:
        if len(configs) == 0:
            return

        render_map_by_config = self._get_renders(configs)

        for config, renders in render_map_by_config.items():
            if renders and all(
                r.status == cc.ConfigStatus.ACTIVE for r in renders
            ):
                try:
                    config.status = cc.ConfigStatus.ACTIVE.value
                    config.save()
                    LOG.info("Config %s become active", config.uuid)
                except Exception:
                    LOG.exception("Error saving config %s", config.uuid)
            # Undesirable behavior if there are no renders for a config.
            # Log this moment as an error so far.
            # NOTE(akremenetsky): Actually it's possible for node set.
            # But we don't have node sets so far.
            elif not renders:
                LOG.error("No renders found for config %s", config.uuid)

    def _handle_orphan_configs(
        self, outdate_min_period: datetime.timedelta = DEF_OUTDATE_MIN_PERIOD
    ) -> None:
        """Delete orphan configs. The configs without nodes."""
        if self._iteration_number % ORPHAN_CFG_ITERATION_FREQUENCY != 0:
            return

        # Take N oldest handled configs check if they are orphan
        outdated_ts = (
            datetime.datetime.now(datetime.timezone.utc) - outdate_min_period
        )
        outdated_configs = models.Config.objects.get_all(
            filters={"updated_at": dm_filters.LT(outdated_ts)},
            limit=30,
            order_by={"updated_at": "asc"},
        )

        if not outdated_configs:
            return

        orphan_configs = set()

        # A config is considered as orphan if all its owners are deleted.
        for config in outdated_configs:
            if not config.target.are_owners_alive():
                orphan_configs.add(config)
                LOG.debug("Orphan config %s has been detected", config.uuid)

        # Delete orphan configs
        for config in orphan_configs:
            try:
                config.delete()
                LOG.info("Orphan config %s has been deleted", config.uuid)
            except Exception:
                LOG.exception("Error deleting orphan config %s", config.uuid)

        # Mark the outdate configs as handled
        for config in set(outdated_configs) - orphan_configs:
            try:
                config.update(force=True)
            except Exception:
                LOG.exception("Error updating config %s", config.uuid)

    def _iteration(self) -> None:
        with contexts.Context().session_manager():
            config_map_by_status = self._get_configs(
                statuses=[cc.ConfigStatus.NEW, cc.ConfigStatus.IN_PROGRESS]
            )
            new_configs = config_map_by_status[cc.ConfigStatus.NEW]
            in_progress_configs = config_map_by_status[
                cc.ConfigStatus.IN_PROGRESS
            ]

            self._actualize_new_configs(new_configs)
            self._actualize_in_progress_configs(in_progress_configs)

            # NOTE(akremenetsky): Current data model implementation takes some
            # advantage but there are some disadvantages as well. One of them
            # a config isn't deleted if the corresponding node(s) is deleted.
            # So we need to detect such cases and clear orphan configs.
            self._handle_orphan_configs()
