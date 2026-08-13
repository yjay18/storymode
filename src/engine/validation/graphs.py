"""Graph validation for campaign packs."""

from collections import defaultdict
from collections.abc import Mapping

from domain.models.diagnostics import Diagnostic
from domain.models.pack import CampaignPack


def _detect_cycle(
    node: str,
    adj: Mapping[str, list[str]],
    visiting: set[str],
    visited: set[str],
    cycle_path: list[str],
) -> bool:
    """Detect a cycle using DFS."""
    visiting.add(node)
    cycle_path.append(node)

    for neighbor in adj.get(node, []):
        if neighbor in visiting:
            cycle_path.append(neighbor)
            return True
        if neighbor not in visited and _detect_cycle(neighbor, adj, visiting, visited, cycle_path):
            return True

    cycle_path.pop()
    visiting.remove(node)
    visited.add(node)
    return False


def validate_areas(pack: CampaignPack) -> list[Diagnostic]:
    """Validate that area connections are reciprocal."""
    diagnostics: list[Diagnostic] = []

    # Build a fast lookup for connected areas
    area_connections: dict[str, set[str]] = {
        area.id: set(area.connected_area_ids) for area in pack.areas.areas
    }

    for i, area in enumerate(pack.areas.areas):
        for connected_id in area.connected_area_ids:
            if connected_id not in area_connections:
                # Handled by references validation if missing globally
                continue

            if area.id not in area_connections[connected_id]:
                diagnostics.append(
                    Diagnostic(
                        file="areas.json",
                        json_pointer=f"/areas/{i}/connected_area_ids",
                        code="missing_reciprocal_connection",
                        message=(
                            f"Area '{area.id}' connects to '{connected_id}', "
                            f"but '{connected_id}' does not connect back."
                        ),
                        related_ids=[area.id, connected_id],
                    )
                )

    return sorted(diagnostics)


def validate_skill_trees(pack: CampaignPack) -> list[Diagnostic]:
    """Validate that skill trees are acyclic (DAG)."""
    diagnostics: list[Diagnostic] = []

    for i, tree in enumerate(pack.skills.skill_trees):
        adj: dict[str, list[str]] = defaultdict(list)
        for edge in tree.edges:
            adj[edge.source_node_id].append(edge.target_node_id)

        visited: set[str] = set()

        for node in (n.id for n in tree.nodes):
            if node not in visited:
                visiting: set[str] = set()
                cycle_path: list[str] = []
                if _detect_cycle(node, adj, visiting, visited, cycle_path):
                    path_str = " -> ".join(cycle_path)
                    diagnostics.append(
                        Diagnostic(
                            file="skills.json",
                            json_pointer=f"/skill_trees/{i}/edges",
                            code="skill_tree_cycle",
                            message=f"Cycle detected in skill tree '{tree.id}': {path_str}",
                            related_ids=list(set(cycle_path)),
                        )
                    )
                    break  # Report one cycle per tree is enough

    return sorted(diagnostics)


def validate_milestones(pack: CampaignPack) -> list[Diagnostic]:
    """Validate milestone reachability and illegal cycles."""
    diagnostics: list[Diagnostic] = []

    milestone_index = {m.id: m for m in pack.plot.milestones}
    adj: dict[str, list[str]] = {m.id: m.valid_next_milestone_ids for m in pack.plot.milestones}

    # 1. Reachability from start milestones
    reachable_from_start: set[str] = set()
    queue = list(pack.plot.start_milestone_ids)

    while queue:
        node = queue.pop(0)
        if node not in reachable_from_start:
            reachable_from_start.add(node)
            queue.extend(adj.get(node, []))

    for i, m in enumerate(pack.plot.milestones):
        if m.id not in reachable_from_start:
            diagnostics.append(
                Diagnostic(
                    file="plot.json",
                    json_pointer=f"/milestones/{i}/id",
                    code="unreachable_milestone",
                    message=f"Milestone '{m.id}' is unreachable from any start milestone.",
                    related_ids=[m.id],
                )
            )

    # 2. Check if every milestone can reach an ending
    ending_ids = set(pack.plot.ending_milestone_ids)
    memo: dict[str, bool] = {}

    def can_reach_ending(node: str, visiting: set[str]) -> bool:
        if node in ending_ids:
            return True
        if node in memo:
            return memo[node]
        if node in visiting:
            return False

        visiting.add(node)
        for neighbor in adj.get(node, []):
            if can_reach_ending(neighbor, visiting):
                memo[node] = True
                visiting.remove(node)
                return True

        visiting.remove(node)
        memo[node] = False
        return False

    for i, m in enumerate(pack.plot.milestones):
        if not can_reach_ending(m.id, set()):
            diagnostics.append(
                Diagnostic(
                    file="plot.json",
                    json_pointer=f"/milestones/{i}/valid_next_milestone_ids",
                    code="dead_end_milestone",
                    message=f"Milestone '{m.id}' cannot reach any ending milestone.",
                    related_ids=[m.id],
                )
            )

    # 3. Illegal cycles
    def detect_illegal_cycles(
        node: str, visiting: set[str], visited: set[str], cycle_path: list[str]
    ) -> list[list[str]]:
        cycles = []
        visiting.add(node)
        cycle_path.append(node)

        for neighbor in adj.get(node, []):
            if neighbor in visiting:
                # Found a cycle, trace back to get just the cycle part
                idx = cycle_path.index(neighbor)
                cycle = [*cycle_path[idx:], neighbor]
                cycles.append(cycle)
            elif neighbor not in visited:
                cycles.extend(detect_illegal_cycles(neighbor, visiting, visited, cycle_path))

        cycle_path.pop()
        visiting.remove(node)
        visited.add(node)
        return cycles

    all_cycles = []
    visited: set[str] = set()
    for m in pack.plot.milestones:
        if m.id not in visited:
            all_cycles.extend(detect_illegal_cycles(m.id, set(), visited, []))

    # Filter cycles to find those that contain a milestone where cycle_allowed=False
    reported_cycles = set()
    for cycle in all_cycles:
        # A cycle is illegal if ANY milestone in it has cycle_allowed=False
        illegal_milestones = [
            n for n in cycle[:-1] if n in milestone_index and not milestone_index[n].cycle_allowed
        ]
        if illegal_milestones:
            cycle_tuple = tuple(cycle)
            if cycle_tuple not in reported_cycles:
                reported_cycles.add(cycle_tuple)
                path_str = " -> ".join(cycle)
                ill_str = ", ".join(illegal_milestones)

                # Find the index of the first illegal milestone for the JSON pointer
                first_ill = illegal_milestones[0]
                pointer = "/milestones"
                for i, m in enumerate(pack.plot.milestones):
                    if m.id == first_ill:
                        pointer = f"/milestones/{i}/cycle_allowed"
                        break

                diagnostics.append(
                    Diagnostic(
                        file="plot.json",
                        json_pointer=pointer,
                        code="illegal_milestone_cycle",
                        message=f"Illegal cycle detected involving [{ill_str}]: {path_str}",
                        related_ids=list(set(cycle)),
                    )
                )

    return sorted(diagnostics)


def validate_opportunities(pack: CampaignPack) -> list[Diagnostic]:
    """Validate opportunity relationships."""
    diagnostics: list[Diagnostic] = []

    milestone_ids = {m.id for m in pack.plot.milestones}
    for i, opp in enumerate(pack.plot.authored_opportunities):
        if opp.parent_milestone_id not in milestone_ids:
            # If VALID-02 validates the reference, it will complain, but the checklist
            # asks for opportunity parents here, so we double-check logic consistency.
            diagnostics.append(
                Diagnostic(
                    file="plot.json",
                    json_pointer=f"/authored_opportunities/{i}/parent_milestone_id",
                    code="unknown_opportunity_parent",
                    message=(
                        f"Opportunity '{opp.id}' references unknown "
                        f"parent milestone '{opp.parent_milestone_id}'."
                    ),
                    related_ids=[opp.parent_milestone_id],
                )
            )

    return sorted(diagnostics)


def validate_graphs(pack: CampaignPack) -> list[Diagnostic]:
    """Run all graph validations."""
    diagnostics = []
    diagnostics.extend(validate_areas(pack))
    diagnostics.extend(validate_skill_trees(pack))
    diagnostics.extend(validate_milestones(pack))
    diagnostics.extend(validate_opportunities(pack))
    return sorted(diagnostics)
