"""High-availability status from environment."""

from __future__ import annotations

import os

from msgate.schemas.health import HAModeStatus


def read_ha_status() -> HAModeStatus:
    node_id = os.environ.get("MSGATE_NODE_ID", "node-1")
    role = os.environ.get("MSGATE_HA_ROLE", "standalone")
    vrrp = os.environ.get("MSGATE_VRRP_STATE", "UNKNOWN")
    leader = os.environ.get("MSGATE_HA_LEADER", node_id)
    return HAModeStatus(node_id=node_id, role=role, vrrp_state=vrrp, leader_node=leader)
