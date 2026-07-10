"""Topology registry. Importing this package registers every topology.

v1 ports:   supermesh, opposing_t, wheatstone, ladder, vcvs
v2 new:     supernode (floating source), vccs_ladder (transconductance dependent source)
"""
from .base import (  # noqa: F401
    TOP_REF_KEY,
    TOPOLOGY_REGISTRY,
    InconsistentPhysics,
    Topology,
    get_topology,
)
from . import supermesh, opposing_t, wheatstone, ladder, vcvs, supernode, vccs_ladder  # noqa: F401, E402
