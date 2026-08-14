"""Exploration use cases."""

from campaign.storage.save_reader import SaveReader
from campaign.storage.save_writer import SaveWriter
from domain.models.area import AreaDefinition
from domain.models.check_state import CheckOutcomes
from domain.models.runtime_state import RuntimeState
from engine.actions.candidates import Candidate, CandidateSet
from engine.actions.checks import build_pending_check, cancel_pending_check, decide_check_necessity
from engine.actions.creative import CreativeValidator
from engine.actions.operations import OperationValidator
from engine.actions.resolution import CheckResolver
from engine.actions.resolver import EntityResolver
from llm.contracts.action import ActionProposal


class ExplorationUseCases:
    """Use cases for standard exploration and checking."""

    def __init__(
        self,
        save_reader: SaveReader,
        save_writer: SaveWriter,
        entity_resolver: EntityResolver,
        op_validator: OperationValidator,
        creative_validator: CreativeValidator,
        check_resolver: CheckResolver,
        campaign_areas: dict[str, AreaDefinition],  # Simplification: assume areas injected
    ) -> None:
        self.save_reader = save_reader
        self.save_writer = save_writer
        self.entity_resolver = entity_resolver
        self.op_validator = op_validator
        self.creative_validator = creative_validator
        self.check_resolver = check_resolver
        self.campaign_areas = campaign_areas

    def submit_action(
        self,
        campaign_id: str,
        save_id: str,
        proposal: ActionProposal,
        command_id: str,
    ) -> RuntimeState:
        """Submit an LLM action proposal and evaluate it."""
        load_result = self.save_reader.load_save(campaign_id, save_id)
        state = load_result.state
        meta = load_result.meta

        # 1. Resolve candidates
        area = self.campaign_areas.get(state.location.area_id)
        if not area:
            raise ValueError(f"Area {state.location.area_id} not found")

        candidates = CandidateSet(
            [
                *[Candidate(id=obj.id, type="object", name=obj.name) for obj in area.objects],
                *[Candidate(id=res.id, type="npc", name=res.name) for res in area.residents],
            ]
        )

        resolved_candidates = []
        for mention in proposal.entity_mentions:
            target = self.entity_resolver.resolve_mention(mention, candidates)
            if target:
                resolved_candidates.append(target)

        # 2. Validate operations
        standard_ops = {"investigate", "inspect", "search", "travel", "talk", "use_item"}
        if proposal.operation in standard_ops:
            self.op_validator.validate(proposal.operation, resolved_candidates, state)
        else:
            self.creative_validator.validate(
                capability_mentions=proposal.capability_mentions,
                resolved_candidates=resolved_candidates,
                area_objects={obj.id: obj for obj in area.objects},
                state=state,
            )

        # 3. Decide check necessity
        if decide_check_necessity(proposal):
            empty_outcomes = CheckOutcomes(
                natural_1=[], low=[], standard=[], strong=[], natural_20=[]
            )
            target_ids = [c.id for c in resolved_candidates]

            check = build_pending_check(
                command_id=command_id,
                state=state,
                proposal=proposal,
                base_dc=10,
                difficulty_adjustment=0,
                actor_id=state.player.id,
                target_ids=target_ids,
                outcomes=empty_outcomes,
            )
            state = state.model_copy(update={"pending_check": check})

        # 4. Save
        state = state.model_copy(update={"revision": state.revision + 1})
        if meta is not None:
            self.save_writer.write_state(state, meta, None)
        return state

    def resolve_check(
        self,
        campaign_id: str,
        save_id: str,
        use_luck: bool,
    ) -> tuple[RuntimeState, int, str]:
        """Resolve a pending check."""
        load_result = self.save_reader.load_save(campaign_id, save_id)
        state = load_result.state
        meta = load_result.meta

        new_state, roll, band, _effects = self.check_resolver.resolve_check(state, use_luck)
        new_state = new_state.model_copy(update={"revision": new_state.revision + 1})

        if meta is not None:
            self.save_writer.write_state(new_state, meta, None)
        return new_state, roll, str(band)

    def cancel_check(
        self,
        campaign_id: str,
        save_id: str,
    ) -> RuntimeState:
        """Cancel a pending check."""
        load_result = self.save_reader.load_save(campaign_id, save_id)
        state = load_result.state
        meta = load_result.meta

        new_state = cancel_pending_check(state)
        new_state = new_state.model_copy(update={"revision": new_state.revision + 1})

        if meta is not None:
            self.save_writer.write_state(new_state, meta, None)
        return new_state
