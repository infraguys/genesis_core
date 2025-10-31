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
import random
import uuid as sys_uuid
import typing as tp

from restalchemy.common import contexts
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.dm import filters as dm_filters
from gcl_looper.services import basic
from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_core.compute.dm import models
from genesis_core.compute import constants as nc
from genesis_core.compute.scheduler.driver import base

LOG = logging.getLogger(__name__)
BUILDER_REBALANCE_RATE = 100


class NodeSchedulerService(basic.BasicService):

    def __init__(
        self,
        pool_filters: list[base.MachinePoolAbstractFilter],
        pool_weighters: list[base.MachinePoolAbstractWeighter],
        machine_filters: list[base.MachineAbstractFilter],
        machine_weighters: list[base.MachineAbstractWeighter],
        iter_min_period: int = 1,
        iter_pause: float = 0.1,
    ):
        super().__init__(iter_min_period, iter_pause)
        self._pool_filters = pool_filters
        self._pool_weighters = pool_weighters
        self._machine_filters = machine_filters
        self._machine_weighters = machine_weighters

    def _get_pool_builders(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> list[ua_models.UniversalAgent]:
        """Get all active builders."""
        return ua_models.UniversalAgent.objects.get_all(
            filters={
                "status": dm_filters.EQ(nc.BuilderStatus.ACTIVE.value),
                # TODO(akremenetsky): Add something like service type
                "name": dm_filters.Like("compute_pool_builder%"),
            },
            limit=limit,
        )

    def _get_in_update_machines(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> list[models.Machine]:
        """Get all in update machines."""
        return models.Machine.objects.get_all(
            filters={
                "pool": dm_filters.IsNot(None),
                "builder": dm_filters.Is(None),
                "build_status": dm_filters.EQ(
                    nc.MachineBuildStatus.IN_BUILD.value
                ),
            },
            limit=limit,
        )

    def _get_machines_for_nodes(
        self, nodes: tp.Collection[sys_uuid.UUID]
    ) -> list[models.Machine]:
        """Get all machines for nodes."""
        return models.Machine.objects.get_all(
            filters={
                "node": dm_filters.In(nodes),
            },
        )

    def _get_unscheduled_nodes(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tuple[base.NodeBundle, ...]:
        unscheduled = models.UnscheduledNode.objects.get_all(limit=limit)

        if not unscheduled:
            return tuple()

        volumes = models.Volume.objects.get_all(
            filters={
                "node": dm_filters.In([u.uuid for u in unscheduled]),
            },
        )
        volume_map = {}
        for v in volumes:
            volume_map.setdefault(v.node, []).append(v)

        return tuple(
            base.NodeBundle(node=u.node, volumes=volume_map.get(u.uuid, []))
            for u in unscheduled
        )

    def _get_unscheduled_volumes(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> list[models.UnscheduledVolume]:
        """Get all unscheduled volumes."""
        return models.UnscheduledVolume.objects.get_all(limit=limit)

    # def _get_unscheduled_machines(
    #     self, limit: int = nc.DEF_SQL_LIMIT
    # ) -> tuple[base.MachineBundle, ...]:
    #     """Get all unscheduled machines."""
    #     machines = models.Machine.objects.get_all(
    #         filters={"pool": dm_filters.Is(None)},
    #         limit=limit,
    #     )

    #     if not machines:
    #         return tuple()

    #     volumes = models.MachineVolume.objects.get_all(
    #         filters={
    #             "machine": dm_filters.In([m.uuid for m in machines]),
    #         },
    #     )
    #     volume_map = {}
    #     for v in volumes:
    #         volume_map.setdefault(v.machine, []).append(v)

    #     return tuple(
    #         base.MachineBundle(machine=m, volumes=volume_map.get(m.uuid, []))
    #         for m in machines
    #     )

    def _get_idle_machines(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tuple[base.MachineBundle, ...]:
        idle = models.Machine.objects.get_all(
            filters={
                "node": dm_filters.Is(None),
                "status": dm_filters.EQ(nc.MachineStatus.IDLE.value),
            },
            limit=limit,
        )

        if not idle:
            return tuple()

        volumes = models.MachineVolume.objects.get_all(
            filters={
                "machine": dm_filters.In([m.uuid for m in idle]),
            },
        )
        volume_map = {}
        for v in volumes:
            volume_map.setdefault(v.machine, []).append(v)

        return tuple(
            base.MachineBundle(machine=m, volumes=volume_map.get(m.uuid, []))
            for m in idle
        )

    def _get_unscheduled_pools(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> list[models.MachinePool]:
        """Get all unscheduled pools."""
        return models.MachinePool.objects.get_all(
            filters={"builder": dm_filters.Is(None)},
            limit=limit,
        )

    def _get_pools(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> list[base.MachinePoolBundle]:
        """Fetch pools and available volumes in the pools."""
        pools = models.MachinePool.objects.get_all(
            filters={
                "status": dm_filters.EQ(nc.MachinePoolStatus.ACTIVE.value),
                "machine_type": dm_filters.EQ(nc.NodeType.VM.value),
                "builder": dm_filters.IsNot(None),
                "driver_spec": dm_filters.NE("{}"),
            },
            limit=limit,
        )
        volumes = models.MachineVolume.objects.get_all(
            filters={
                "pool": dm_filters.In(p.uuid for p in pools),
                "machine": dm_filters.Is(None),
                "node_volume": dm_filters.Is(None),
            },
        )
        volume_map = {}
        for v in volumes:
            volume_map.setdefault(v.pool, []).append(v)

        return tuple(
            base.MachinePoolBundle(pool=p, volumes=volume_map.get(p.uuid, []))
            for p in pools
        )

    # def _build_root_volume(
    #     self, node: models.UnscheduledNode
    # ) -> models.Volume:
    #     volume_name = "root-volume"
    #     volume_uuid = sys_uuid.uuid5(node.uuid, volume_name)
    #     volume = models.Volume(
    #         uuid=volume_uuid,
    #         name=volume_name,
    #         size=node.root_disk_size,
    #         node=node.uuid,
    #         project_id=node.project_id,
    #         index=0,
    #     )

    #     return volume

    # def _create_machines_for(
    #     self, unscheduled: list[models.UnscheduledNode]
    # ) -> list[models.Machine]:
    #     """Create machines for unscheduled nodes."""
    #     machines = []
    #     if not unscheduled:
    #         LOG.debug("Nothing to schedule, no unscheduled nodes")
    #         return machines

    #     for node in unscheduled:
    #         # TODO(akremenetsky): It's a builder work.
    #         # Move to the builder service.
    #         if node.root_disk_size:
    #             try:
    #                 volume = self._build_root_volume(node)
    #                 volume.insert()
    #                 LOG.info(
    #                     "The root volume %s has been created", volume.uuid
    #                 )
    #             except ra_exceptions.ConflictRecords:
    #                 # It's ok, the volume is already created
    #                 pass

    #         machines.append(self._build_vm(node))

    #     return machines
    def _build_machine_volume(
        pool: base.MachinePoolBundle, volume: models.Volume
    ) -> models.MachineVolume:
        # TODO(akremenetsky): Rework this simple implementation.
        # At the moment we just take the first storage pool
        # and allocate additional space for the volume.
        # But we need to figure out which storage pool is
        # the owner of the volume.
        storage_pool = next(iter(pool.storage_pool_map.values()))
        storage_pool["avail_size"] -= volume.size

        pool_volume = models.MachineVolume(
            uuid=volume.uuid,
            volume=volume.uuid,
            index=volume.index,
            size=volume.size,
            image=volume.image,
            boot=volume.boot,
            label=volume.label,
            device_type=volume.device_type,
            node_volume=volume.uuid,
        )

        return pool_volume

    def _place_volume_into_pool(
        self, volume: models.Volume, pool: base.MachinePoolBundle
    ) -> models.MachineVolume:
        """Place a volume into a pool.

        The scheduling operation has been completed. A particular pool
        has been selected for the volume. Now we need to place the volume
        into the pool.
        """

        # Don't waste time on volumes without an image.
        # Create a new volume.
        if volume.image is None:
            return self._build_machine_volume(pool, volume)

        volumes = []
        for pool_volume in pool.volumes:
            # We can take less than required size and resize it later
            # NOTE(akremenetsky): Need to think about target fileds for
            # volumes. Is the size is a target or actual field?
            if (
                pool_volume.image == volume.image
                and pool_volume.size <= volume.size
            ):
                volumes.append(pool_volume)

        # No volumes found, just create a new volume later
        if not volumes:
            return self._build_machine_volume(pool, volume)

        # Figure out the best volume
        volumes.sort(key=lambda v: node_volume.size - v.size)
        pool_volume = volumes[0]
        need_size = node_volume.size - pool_volume.size

        # TODO(akremenetsky): Rework this simple implementation.
        # At the moment we just take the first storage pool
        # and allocate additional space for the volume.
        # But we need to figure out which storage pool is
        # the owner of the volume.
        storage_pool = pool.storage_pool_map.values()[0]

        # Check if the storage pool has enough space
        if need_size and storage_pool["avail_size"] < need_size:
            return self._build_machine_volume(pool, volume)

        # Allocate additional space for the volume
        storage_pool["avail_size"] -= need_size

        # Remove the volume from the pool
        pool.volumes.remove(pool_volume)
        LOG.debug(
            "Found machine volume %s for node volume %s",
            pool_volume,
            volume,
        )

        return pool_volume

    def _place_node_into_pool(
        self, node: base.NodeBundle, pool: base.MachinePoolBundle
    ) -> None:
        """Place a node into a pool.

        The scheduling operation has been completed. A particular pool
        has been selected for the node. Now we need to place the node
        into the pool.
        """
        # Prepare the machine
        machine_uuid = node.node.uuid
        machine = models.Machine(
            uuid=machine_uuid,
            firmware_uuid=machine_uuid,
            name=node.node.name,
            cores=node.node.cores,
            ram=node.node.ram,
            node=node.node.uuid,
            project_id=node.node.project_id,
            machine_type=nc.NodeType.VM.value,
            status=nc.MachineStatus.SCHEDULED.value,
        )

        # Place volumes into the pool
        volume_allocations = []
        for node_volume in node.volumes:
            volume_allocations.append(
                self._place_volume_into_pool(node_volume, pool)
            )

        # Set pool to machine
        machine.pool = pool.pool.uuid
        machine.save()
        for volume in volume_allocations:
            volume.pool = pool.pool.uuid
            volume.machine = machine_uuid
            volume.save()

        LOG.info(
            "The machine %s scheduled to %s pool",
            machine.uuid,
            pool.pool.uuid,
        )

        # Actualize pool after scheduling machine to it.
        # We need consider the machine we just scheduled
        # for next machines in this cycle
        pool.pool.avail_cores -= machine.cores
        pool.pool.avail_ram -= machine.ram

    def _schedule_on_existing_machines(self) -> tuple[base.MachineBundle, ...]:
        unscheduled = self._get_unscheduled_nodes()

        # TODO(akremenetsky): Idle machines are limited by some number
        # in SQL query and it's maybe a problem if we have a lot of
        # idle machines. The fetched machines may be not suitable for
        # unscheduled nodes and we will create another machines.
        idle_machines = self._get_idle_machines()

        idle_hws = [
            m
            for m in idle_machines
            if m.machine.machine_type == nc.NodeType.HW.value
        ]
        idle_vms = [
            m
            for m in idle_machines
            if m.machine.machine_type == nc.NodeType.VM.value
        ]
        vms = []

        for unscheduled_node in unscheduled:
            node: models.Node = unscheduled_node.node
            if node.node_type == nc.NodeType.HW:
                idle_machines = idle_hws
            else:
                idle_machines = idle_vms

            # Filtering. We filter out unsuitable machines. For instance,
            # machines that doesn't have enough cores or ram or some
            # placement constraints.
            for filter in self._machine_filters:
                idle_machines = filter.filter(unscheduled_node, idle_machines)

            # There are no available HW machines for this node
            # This means we unable to proceed scheduling process
            # for this node.
            if not idle_machines and node.node_type == nc.NodeType.HW:
                LOG.warning(
                    "No HW machines found to schedule node %s",
                    node.uuid,
                )
                if node.status != nc.NodeStatus.ERROR:
                    node.status = nc.NodeStatus.ERROR.value
                    node.description = "No suitable HW machines found"
                    node.save()
                continue

            # There are no available VM machines for this node
            # but it's not a problem. A virtual machine will be
            # created later.
            if not idle_machines and node.node_type == nc.NodeType.VM:
                LOG.debug(
                    "No idle VM machines found to schedule node %s",
                    node.uuid,
                )
                vms.append(unscheduled_node)
                continue

            # Weighting. We weight machines and choose the best one.
            # Accumulate weights from all weighters.
            # So that the best pool has the highest weight
            accumulated_weights = [0.0] * len(idle_machines)
            for weighter in self._machine_weighters:
                weights = weighter.weight(idle_machines)
                accumulated_weights = [
                    w0 + w1 for w0, w1 in zip(accumulated_weights, weights)
                ]

            # Choose the best machine, it means the one with the highest weight
            index = accumulated_weights.index(max(accumulated_weights))
            machine_bundle = idle_machines[index]

            # TODO(akremenetsky): Map volumes to machine volumes
            machine_bundle.machine.node = node.uuid
            machine_bundle.machine.status = nc.MachineStatus.SCHEDULED.value
            node.status = nc.NodeStatus.SCHEDULED.value
            try:
                node.save()
                machine_bundle.machine.save()
                LOG.info(
                    "The node %s scheduled to %s machine",
                    node.uuid,
                    machine_bundle.machine.uuid,
                )
            except Exception:
                LOG.exception("Error scheduling node %s", node.uuid)

            # Actualize idle machines
            if node.node_type == nc.NodeType.HW.value:
                idle_hws.remove(machine_bundle)
            else:
                idle_vms.remove(machine_bundle)

        return vms

    def _schedule_on_pools(
        self,
        nodes: tp.Collection[base.NodeBundle],
        pools: tp.Collection[base.MachinePoolBundle],
    ) -> None:
        if not nodes:
            LOG.debug("Nothing to schedule, no unscheduled nodes")
            return

        if not pools:
            _nodes = (m.node.uuid for m in nodes)
            LOG.warning("No pools found to schedule nodes %s", _nodes)
            return

        for node in nodes:
            # Filtering. We filter out unsuitable pools. For instance, pools
            # that doesn't have enough cores or ram or some placement
            # constraints.
            for filter in self._pool_filters:
                pools = filter.filter(node, pools)

            if not pools:
                LOG.warning(
                    "No pools found to schedule node %s", node.node.uuid
                )
                continue

            # Weighting. We weight pools and choose the best one.
            # For instance, most free pool is the best.

            # Accumulate weights from all weighters
            # So that the best pool has the highest weight
            accumulated_weights = [0.0] * len(pools)
            for weighter in self._pool_weighters:
                weights = weighter.weight(pools)
                accumulated_weights = [
                    w0 + w1 for w0, w1 in zip(accumulated_weights, weights)
                ]

            # Choose the best pool, it means the one with the highest weight
            index = accumulated_weights.index(max(accumulated_weights))
            pool = pools[index]
            if not pool:
                LOG.warning(
                    "No pools found to schedule node %s", node.node.uuid
                )
                continue

            # The final step is to place the node into the pool
            try:
                self._place_node_into_pool(node, pool)
            except Exception:
                LOG.exception(
                    "Error placing node %s into pool %s",
                    node.node.uuid,
                    pool.pool.uuid,
                )

    def _schedule_pools(
        self, pool_builders: list[ua_models.UniversalAgent]
    ) -> None:
        unsheduled = self._get_unscheduled_pools()
        if not unsheduled:
            LOG.debug("Nothing to schedule, no unscheduled pools")
            return

        # The simplest implementation is to schedule to a random machine agent
        if not pool_builders:
            pools = [pool.uuid for pool in unsheduled]
            LOG.warning("No pool builders found to schedule pools %s", pools)
            return

        for pool in unsheduled:
            builder = random.choice(pool_builders)

            try:
                pool.builder = builder.uuid
                pool.update()
                LOG.info(
                    "The pool %s scheduled to builder %s",
                    pool.uuid,
                    builder.uuid,
                )
            except Exception:
                LOG.exception("Error scheduling pool %s", pool.uuid)

    def _schedule_volume_on_pools(
        self, pools: list[models.MachinePool]
    ) -> None:
        """Schedule volumes on pools."""
        unscheduled_volumes = self._get_unscheduled_volumes()
        if not unscheduled_volumes:
            LOG.debug("Nothing to schedule, no unscheduled volumes")
            return

        pools = {p.pool.uuid: p for p in pools}

        machines = self._get_machines_for_nodes(
            unscheduled.volume.node
            for unscheduled in unscheduled_volumes
            if unscheduled.volume.node is not None
        )
        node_map = {m.node: m for m in machines}

        for unscheduled in unscheduled_volumes:
            volume = unscheduled.volume

            # Unknown case, just skip it
            if volume.node is None:
                LOG.debug(
                    "Volume %s is not assigned to any node, skipping",
                    volume.uuid,
                )
                continue

            # Unknown node case, just skip it
            if volume.node not in node_map:
                LOG.error(
                    "Volume %s is assigned to unknown node %s",
                    volume.uuid,
                    volume.node,
                )
                continue

            try:
                pool = pools[node_map[volume.node].pool]
            except KeyError:
                LOG.error(
                    "Unable to find pool for volume %s assigned to node %s",
                    volume.uuid,
                    volume.node,
                )
                continue

            # Place the volume into the same pool as the machine
            try:
                machine_volume = self._place_volume_into_pool(volume, pool)
                machine_volume.pool = pool.uuid
                machine_volume.save()
            except Exception:
                LOG.exception(
                    "Error placing volume %s into pool %s",
                    volume.uuid,
                    pool.uuid,
                )
                continue

    # def _schedule_in_update(self, builders: list[models.Builder]) -> None:
    #     machines = self._get_in_update_machines()
    #     if not machines:
    #         LOG.debug("No in update machines found")
    #         return

    #     for machine in machines:
    #         try:
    #             builder = random.choice(builders)
    #             machine.builder = builder.uuid
    #             machine.update()
    #             LOG.debug(
    #                 "The machine %s scheduled to builder %s",
    #                 machine.uuid,
    #                 builder.uuid,
    #             )
    #         except Exception:
    #             LOG.exception("Error scheduling machine %s", machine.uuid)

    # def _rebalance_builders(self, builders: list[models.Builder]) -> None:
    #     """Rebalances builders.

    #     There are two reasons why we would like to rebalance builders:
    #     1. The build procedure may be pretty long and some machines may
    #        get stuck waiting for others to be built. A possible solution is
    #        to rebalance loads between the builders.
    #     2. Drop "dead" builders. A builder may receive machines
    #        to build and then become inactive for some reason. In this case,
    #        the machines will be built indefinitely. To handle this case, we
    #        need to "drop" all builders from time to time. All active builders
    #        will register themselves on a new iteration, and all inactive builders
    #        are removed.
    #     """
    #     # Check if the current iteration is a rebalancing point
    #     if self._iteration_number % BUILDER_REBALANCE_RATE != 0:
    #         return

    #     # Delete all builders. They will register on the next iteration.
    #     for builder in builders:
    #         builder.delete()
    #         LOG.debug(
    #             "The builder %s has been deleted for rebalancing", builder.uuid
    #         )

    def _iteration(self):
        with contexts.Context().session_manager():
            pool_builders = self._get_pool_builders()
            pools = self._get_pools()

            # It's not obvious case when there are unscheduled machines
            # How it can happen?
            # unscheduled_machines = self._get_unscheduled_machines()

            if not pool_builders:
                LOG.error("No pool builders found!")
                return

            # Pools
            try:
                self._schedule_pools(pool_builders)
            except Exception:
                LOG.exception("Error scheduling pools:")

            # Nodes
            # The first step is to schedule nodes to existing machines
            # If there are no available machines for a node,
            # the nodes just return
            try:
                unscheduled_nodes = self._schedule_on_existing_machines()
            except Exception:
                LOG.exception("Error scheduling nodes:")
                unscheduled_nodes = []

            # The second step is to schedule unscheduled nodes to pools.
            try:
                self._schedule_on_pools(unscheduled_nodes, pools)
            except Exception:
                LOG.exception("Error scheduling nodes:")

            # Volumes
            try:
                self._schedule_volume_on_pools(pools)
            except Exception:
                LOG.exception("Error scheduling volumes:")

            # Reschedule in update machines.
            # A machine may be updated during its lifetime. For instance,
            # additional volumes will be added or cores will be changes.
            # In such case we need to repeat the scheduling procedure
            # to choose a builder that prepare and reserve all new resources.
            # try:
            #     self._schedule_in_update(builders)
            # except Exception:
            #     LOG.exception("Error scheduling nodes:")

            # There are two reasons why we would like to rebalance builders:
            # 1. The build procedure may be pretty long and some machines may
            #    stuck waiting other will be built. A possible solution is
            #    to rebalance loads between the builders.
            # 2. Drop "dead" builders. A builder may receives machines
            #    to build and then dead for some reason. In this case the
            #    machines will be built infinity time. To handle this case we
            #    need to "drop" all builders time to time. All active builders
            #    will register itself on a new iteration, all dead builders
            #    are removed.
            # self._rebalance_builders(builders)
