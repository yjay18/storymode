"""Closed predicate evaluator over runtime state (PLOT-01)."""

from __future__ import annotations

from domain.models.common import DisplayString, EntityId
from domain.models.plot_state import MilestoneState
from domain.models.runtime_state import RuntimeState


def evaluate_predicate(predicate: str | DisplayString, state: RuntimeState) -> bool:
    """Evaluate a single closed predicate against runtime state."""
    text = str(predicate).strip()
    if not text:
        return True

    # 1. Inversion prefix "!..."
    if text.startswith("!"):
        inner = text[1:].strip()
        return not evaluate_predicate(inner, state)

    # 2. Fact predicates: "fact:X"
    if text.startswith("fact:"):
        fact_id = EntityId(text.split(":", 1)[1].strip())
        return fact_id in state.known_fact_ids

    # 3. Flag predicates: "flag:X", "flag:X=val", "flag:X>=val"
    if text.startswith("flag:"):
        expr = text.split(":", 1)[1].strip()
        if ">=" in expr:
            k, v = expr.split(">=", 1)
            flag_val = state.world_flags.get(EntityId(k.strip()), 0)
            try:
                if isinstance(flag_val, (int, str)):
                    return int(flag_val) >= int(v.strip())
                return False
            except (ValueError, TypeError):
                return False
        if "=" in expr:
            k, v = expr.split("=", 1)
            flag_val_eq = state.world_flags.get(EntityId(k.strip()))
            return str(flag_val_eq).lower() == v.strip().lower()

        flag_val_bool = state.world_flags.get(EntityId(expr))
        return bool(flag_val_bool)

    # 4. Milestone predicates: "milestone:X", "milestone:X=resolved|active|available|locked|failed"
    if text.startswith("milestone:"):
        parts = text.split(":", 1)[1].strip().split("=", 1)
        m_id = EntityId(parts[0].strip())
        expected_status = parts[1].strip().lower() if len(parts) > 1 else "resolved"
        actual_status = state.plot.milestones.get(m_id)

        if expected_status == "locked":
            return actual_status is None or actual_status == MilestoneState.LOCKED
        if actual_status is not None:
            return actual_status.value == expected_status
        return False

    # 5. Level predicates: "min_level:X", "level:X"
    if text.startswith("min_level:") or text.startswith("level:"):
        lvl_val = int(text.split(":", 1)[1].strip())
        return state.player.level >= lvl_val

    # 6. Location predicates: "location:X", "area:X"
    if text.startswith("location:") or text.startswith("area:"):
        area_id = EntityId(text.split(":", 1)[1].strip())
        return state.location.area_id == area_id

    # 7. Clock predicates: "clock:X=completed", "clock:X>=val"
    if text.startswith("clock:"):
        expr = text.split(":", 1)[1].strip()
        if "=completed" in expr:
            clock_id = EntityId(expr.split("=completed")[0].strip())
            clk = state.clocks.get(clock_id)
            return clk is not None and clk.completed
        if ">=" in expr:
            c_id, v = expr.split(">=", 1)
            clk = state.clocks.get(EntityId(c_id.strip()))
            if clk is None:
                return False
            return clk.current >= int(v.strip())

    # 8. Item predicates: "item:X", "item:X>=qty"
    if text.startswith("item:"):
        expr = text.split(":", 1)[1].strip()
        if ">=" in expr:
            item_id_str, qty_str = expr.split(">=", 1)
            item_id = EntityId(item_id_str.strip())
            total = sum(e.quantity for e in state.player.inventory if e.item_id == item_id)
            return total >= int(qty_str.strip())
        item_id = EntityId(expr)
        return any(e.item_id == item_id and e.quantity > 0 for e in state.player.inventory)

    # Fallback to direct entity ID lookup
    target_id = EntityId(text)
    if target_id in state.known_fact_ids:
        return True
    if target_id in state.plot.milestones:
        return state.plot.milestones[target_id] == MilestoneState.RESOLVED
    if target_id in state.world_flags:
        return bool(state.world_flags[target_id])

    return False


def evaluate_all_predicates(
    predicates: list[str | DisplayString],
    state: RuntimeState,
) -> bool:
    """Evaluate a list of predicates; returns True only if all are met."""
    return all(evaluate_predicate(p, state) for p in predicates)
