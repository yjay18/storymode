"""Resolution of pending checks."""

from domain.models.runtime_state import RuntimeState
from domain.models.skill import EffectDefinition, EffectKind
from engine.dice.ports import RandomSource


class CheckResolver:
    """Resolves pending checks atomically."""

    def __init__(self, random_source: RandomSource) -> None:
        self.random_source = random_source

    def resolve_check(
        self, state: RuntimeState, use_luck: bool
    ) -> tuple[RuntimeState, int, str, list[EffectDefinition]]:
        """Resolve the active pending check, applying luck, rolls, and effects."""
        check = state.pending_check
        if not check:
            raise ValueError("No active pending check to resolve")

        new_player = state.player

        # 1. Roll or use luck
        if use_luck:
            if state.player.luck_current < 1:
                raise ValueError("Not enough luck to guarantee success")
            new_player = new_player.model_copy(
                update={"luck_current": state.player.luck_current - 1}
            )
            roll = 20
        else:
            roll = self.random_source.roll(20)

        # 2. Evaluate outcome band
        effects: list[EffectDefinition] = []
        band_name = ""

        if roll == 1:
            band_name = "natural_1"
            effects = check.allowed_outcomes.natural_1
        elif roll == 20:
            band_name = "natural_20"
            effects = check.allowed_outcomes.natural_20
        elif roll >= check.final_dc + 5:
            band_name = "strong"
            effects = check.allowed_outcomes.strong
        elif roll >= check.final_dc:
            band_name = "standard"
            effects = check.allowed_outcomes.standard
        else:
            band_name = "low"
            effects = check.allowed_outcomes.low

        # 3. Apply effects
        new_state = state.model_copy(update={"player": new_player, "pending_check": None})
        new_state = self._apply_effects(new_state, check.actor_id, check.target_ids, effects)

        return new_state, roll, band_name, effects

    def _apply_effects(
        self,
        state: RuntimeState,
        actor_id: str,
        target_ids: list[str],
        effects: list[EffectDefinition],
    ) -> RuntimeState:
        """Apply a list of effects to the state (returns new state)."""
        new_state = state

        for effect in effects:
            if effect.kind == EffectKind.DAMAGE:
                if target_ids:
                    t_id = target_ids[0]
                    if t_id == new_state.player.id:
                        new_hp = max(0, new_state.player.hp.current - effect.magnitude)
                        new_hp_val = new_state.player.hp.model_copy(update={"current": new_hp})
                        new_player = new_state.player.model_copy(update={"hp": new_hp_val})
                        new_state = new_state.model_copy(update={"player": new_player})
                    else:
                        comp = new_state.party.companions.get(t_id)
                        if comp:
                            new_hp = max(0, comp.hp.current - effect.magnitude)
                            new_hp_val = comp.hp.model_copy(update={"current": new_hp})
                            new_comp = comp.model_copy(update={"hp": new_hp_val})
                            new_comps = dict(new_state.party.companions)
                            new_comps[t_id] = new_comp
                            new_party = new_state.party.model_copy(update={"companions": new_comps})
                            new_state = new_state.model_copy(update={"party": new_party})

            elif effect.kind == EffectKind.HEAL and target_ids:
                t_id = target_ids[0]
                if t_id == new_state.player.id:
                    new_hp = min(
                        new_state.player.hp.maximum,
                        new_state.player.hp.current + effect.magnitude,
                    )
                    new_hp_val = new_state.player.hp.model_copy(update={"current": new_hp})
                    new_player = new_state.player.model_copy(update={"hp": new_hp_val})
                    new_state = new_state.model_copy(update={"player": new_player})
                else:
                    comp = new_state.party.companions.get(t_id)
                    if comp:
                        new_hp = min(comp.hp.maximum, comp.hp.current + effect.magnitude)
                        new_hp_val = comp.hp.model_copy(update={"current": new_hp})
                        new_comp = comp.model_copy(update={"hp": new_hp_val})
                        new_comps = dict(new_state.party.companions)
                        new_comps[t_id] = new_comp
                        new_party = new_state.party.model_copy(update={"companions": new_comps})
                        new_state = new_state.model_copy(update={"party": new_party})

        return new_state
