"""Tests for graph validation."""

from unittest.mock import MagicMock

from engine.validation.graphs import (
    validate_areas,
    validate_milestones,
    validate_opportunities,
    validate_skill_trees,
)


def test_validate_areas_reciprocal() -> None:
    pack = MagicMock()

    area1 = MagicMock()
    area1.id = "area-1"
    area1.connected_area_ids = ["area-2"]

    area2 = MagicMock()
    area2.id = "area-2"
    area2.connected_area_ids = ["area-1"]

    pack.areas.areas = [area1, area2]

    diagnostics = validate_areas(pack)
    assert len(diagnostics) == 0


def test_validate_areas_missing_reciprocal() -> None:
    pack = MagicMock()

    area1 = MagicMock()
    area1.id = "area-1"
    area1.connected_area_ids = ["area-2"]

    area2 = MagicMock()
    area2.id = "area-2"
    area2.connected_area_ids = []

    pack.areas.areas = [area1, area2]

    diagnostics = validate_areas(pack)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "missing_reciprocal_connection"
    assert diagnostics[0].file == "areas.json"


def test_validate_skill_trees_acyclic() -> None:
    pack = MagicMock()

    tree = MagicMock()
    tree.id = "tree-1"

    n1 = MagicMock()
    n1.id = "n1"
    n2 = MagicMock()
    n2.id = "n2"
    tree.nodes = [n1, n2]

    e1 = MagicMock()
    e1.source_node_id = "n1"
    e1.target_node_id = "n2"
    tree.edges = [e1]

    pack.skills.skill_trees = [tree]

    diagnostics = validate_skill_trees(pack)
    assert len(diagnostics) == 0


def test_validate_skill_trees_cycle() -> None:
    pack = MagicMock()

    tree = MagicMock()
    tree.id = "tree-1"

    n1 = MagicMock()
    n1.id = "n1"
    n2 = MagicMock()
    n2.id = "n2"
    tree.nodes = [n1, n2]

    e1 = MagicMock()
    e1.source_node_id = "n1"
    e1.target_node_id = "n2"

    e2 = MagicMock()
    e2.source_node_id = "n2"
    e2.target_node_id = "n1"

    tree.edges = [e1, e2]
    pack.skills.skill_trees = [tree]

    diagnostics = validate_skill_trees(pack)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "skill_tree_cycle"


def test_validate_milestones_success() -> None:
    pack = MagicMock()

    m1 = MagicMock()
    m1.id = "m1"
    m1.cycle_allowed = False
    m1.valid_next_milestone_ids = ["m2"]

    m2 = MagicMock()
    m2.id = "m2"
    m2.cycle_allowed = False
    m2.valid_next_milestone_ids = []

    pack.plot.milestones = [m1, m2]
    pack.plot.start_milestone_ids = ["m1"]
    pack.plot.ending_milestone_ids = ["m2"]

    diagnostics = validate_milestones(pack)
    assert len(diagnostics) == 0


def test_validate_milestones_unreachable_and_dead_end() -> None:
    pack = MagicMock()

    m1 = MagicMock()
    m1.id = "m1"
    m1.cycle_allowed = False
    m1.valid_next_milestone_ids = ["m2"]

    m2 = MagicMock()
    m2.id = "m2"
    m2.cycle_allowed = False
    m2.valid_next_milestone_ids = []

    m3 = MagicMock()
    m3.id = "m3"
    m3.cycle_allowed = False
    m3.valid_next_milestone_ids = ["m4"]

    m4 = MagicMock()
    m4.id = "m4"
    m4.cycle_allowed = False
    m4.valid_next_milestone_ids = []

    pack.plot.milestones = [m1, m2, m3, m4]
    pack.plot.start_milestone_ids = ["m1"]
    pack.plot.ending_milestone_ids = ["m2"]

    diagnostics = validate_milestones(pack)
    # m3 is unreachable from m1
    # m4 is unreachable from m1
    # m3 goes to m4, which doesn't reach ending.
    # Therefore m3 is dead end, m4 is dead end.

    assert len(diagnostics) == 4
    codes = {d.code for d in diagnostics}
    assert "unreachable_milestone" in codes
    assert "dead_end_milestone" in codes


def test_validate_milestones_illegal_cycle() -> None:
    pack = MagicMock()

    m1 = MagicMock()
    m1.id = "m1"
    m1.cycle_allowed = False
    m1.valid_next_milestone_ids = ["m2"]

    m2 = MagicMock()
    m2.id = "m2"
    m2.cycle_allowed = True
    m2.valid_next_milestone_ids = ["m3"]

    m3 = MagicMock()
    m3.id = "m3"
    m3.cycle_allowed = False  # This makes the cycle illegal!
    m3.valid_next_milestone_ids = ["m2", "m4"]

    m4 = MagicMock()
    m4.id = "m4"
    m4.cycle_allowed = False
    m4.valid_next_milestone_ids = []

    pack.plot.milestones = [m1, m2, m3, m4]
    pack.plot.start_milestone_ids = ["m1"]
    pack.plot.ending_milestone_ids = ["m4"]

    diagnostics = validate_milestones(pack)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "illegal_milestone_cycle"


def test_validate_opportunities_unknown_parent() -> None:
    pack = MagicMock()
    pack.plot.milestones = []

    opp = MagicMock()
    opp.id = "opp1"
    opp.parent_milestone_id = "unknown"
    pack.plot.authored_opportunities = [opp]

    diagnostics = validate_opportunities(pack)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "unknown_opportunity_parent"
