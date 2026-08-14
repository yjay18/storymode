"""Tests for runtime opportunity proposal validation (PLOT-03)."""

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.common import DisplayString, EntityId
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot import MilestoneDefinition, OpportunityDefinition, PlotFile
from domain.models.plot_state import MilestoneState, PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState
from engine.plot.proposal_validator import (
    OpportunityCandidateSet,
    OpportunityProposalV1,
    validate_opportunity_proposal,
)

# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

_STATS = StatBlock(
    strength=10,
    dexterity=10,
    intelligence=10,
    charisma=10,
    constitution=10,
    wisdom=10,
)
_RES = ResourceValue(current=10, maximum=10)
_ZERO = ResourceValue(current=0, maximum=5)


def _make_candidate_set() -> OpportunityCandidateSet:
    return OpportunityCandidateSet(
        milestones=[EntityId("m_active_1"), EntityId("m_locked_2")],
        entities=[EntityId("npc_blacksmith"), EntityId("item_key")],
        outcomes=[EntityId("outcome_success"), EntityId("outcome_partial")],
        predicates=[
            DisplayString("fact:discovered_clue"),
            DisplayString("fact:time_expired"),
        ],
    )


def _make_proposal(
    parent_ordinal: int = 1,
    title: str = "Infiltrate the Cellar",
    entity_ordinals: list[int] | None = None,
    allowed_outcome_ordinals: list[int] | None = None,
    precondition_ordinals: list[int] | None = None,
    expiry_condition_ordinals: list[int] | None = None,
    canonical_claims: list[str] | None = None,
    balance_rating: int = 50,
) -> OpportunityProposalV1:
    return OpportunityProposalV1(
        request_id=EntityId("req-opp-1"),
        parent_milestone_ordinal=parent_ordinal,
        title=DisplayString(title),
        description=DisplayString("A secret tunnel has been uncovered."),
        entity_ordinals=entity_ordinals or [1],
        approach_tags=[DisplayString("stealth")],
        allowed_outcome_ordinals=allowed_outcome_ordinals or [1],
        precondition_ordinals=precondition_ordinals or [1],
        expiry_condition_ordinals=expiry_condition_ordinals or [2],
        challenge_label=DisplayString("Stealth Infiltration"),
        pacing_reason=DisplayString("Adds optional side challenge."),
        canonical_claims=[DisplayString(c) for c in (canonical_claims or [])],
        balance_rating=balance_rating,
    )


def _make_state(active_milestones: set[str] | None = None) -> RuntimeState:
    active_m = active_milestones or {"m_active_1"}
    milestones_dict = {EntityId(m): MilestoneState.ACTIVE for m in active_m}
    player = PlayerState(
        id=EntityId("hero"),
        name=DisplayString("Hero"),
        background_id=EntityId("bg-1"),
        stats=_STATS,
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        mana_regen=2,
        speed=30,
        luck_current=0,
        luck_capacity=3,
    )
    return RuntimeState(
        campaign_id=EntityId("camp"),
        campaign_version="1.0.0",
        campaign_fingerprint="fp",
        save_id=EntityId("save"),
        revision=0,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(protagonist_id=EntityId("hero")),
        location=LocationState(area_id=EntityId("town")),
        plot=PlotState(
            milestones=milestones_dict,
            current_milestone_ids={EntityId(m) for m in active_m},
        ),
    )


def _make_plot_file(
    authored_opps: list[OpportunityDefinition] | None = None,
) -> PlotFile:
    m = MilestoneDefinition(
        id=EntityId("m_active_1"),
        canonical_truth=DisplayString("Truth"),
        narrative_purpose=DisplayString("Purpose"),
        required_outcome_ids=[EntityId("out_1")],
        allowed_approach_tags=[],
        forbidden_changes=[],
        preconditions=[],
        valid_next_milestone_ids=[],
        difficulty_band=DisplayString("standard"),
        pacing_weight=50,
        cycle_allowed=False,
    )
    return PlotFile(
        campaign_id=EntityId("camp"),
        campaign_version="1.0.0",
        start_milestone_ids=[EntityId("m_active_1")],
        milestones=[m],
        authored_opportunities=authored_opps or [],
        ending_milestone_ids=[EntityId("m_end")],
        clock_definitions=[],
    )


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------


def test_validate_valid_proposal() -> None:
    proposal = _make_proposal()
    candidate_set = _make_candidate_set()
    state = _make_state()
    plot_file = _make_plot_file()

    call_count = 0

    def mock_generator() -> EntityId:
        nonlocal call_count
        call_count += 1
        return EntityId("opp-runtime-1")

    result = validate_opportunity_proposal(
        proposal, candidate_set, state, plot_file, mock_generator
    )

    assert result.is_valid
    assert not result.diagnostics
    assert call_count == 1
    assert result.opportunity_def is not None
    assert result.opportunity_def.id == EntityId("opp-runtime-1")
    assert result.opportunity_def.parent_milestone_id == EntityId("m_active_1")
    assert result.opportunity_def.allowed_outcome_ids == [EntityId("outcome_success")]
    assert result.opportunity_instance is not None
    assert result.opportunity_instance.opportunity_id == EntityId("opp-runtime-1")


def test_validate_rejects_canonical_claims() -> None:
    proposal = _make_proposal(canonical_claims=["The king was secretly an imposter all along!"])
    candidate_set = _make_candidate_set()
    state = _make_state()
    plot_file = _make_plot_file()

    call_count = 0

    def mock_generator() -> EntityId:
        nonlocal call_count
        call_count += 1
        return EntityId("opp-runtime-1")

    result = validate_opportunity_proposal(
        proposal, candidate_set, state, plot_file, mock_generator
    )

    assert not result.is_valid
    assert call_count == 0  # No ID consumed!
    assert any("canonical claims" in d for d in result.diagnostics)


def test_validate_rejects_out_of_range_milestone_ordinal() -> None:
    proposal = _make_proposal(parent_ordinal=99)
    candidate_set = _make_candidate_set()
    state = _make_state()
    plot_file = _make_plot_file()

    call_count = 0

    def mock_generator() -> EntityId:
        nonlocal call_count
        call_count += 1
        return EntityId("opp-runtime-1")

    result = validate_opportunity_proposal(
        proposal, candidate_set, state, plot_file, mock_generator
    )

    assert not result.is_valid
    assert call_count == 0
    assert any("parent_milestone_ordinal" in d for d in result.diagnostics)


def test_validate_rejects_inactive_parent_milestone() -> None:
    # Ordinal 2 corresponds to m_locked_2 which is not in current_milestones
    proposal = _make_proposal(parent_ordinal=2)
    candidate_set = _make_candidate_set()
    state = _make_state(active_milestones={"m_active_1"})
    plot_file = _make_plot_file()

    call_count = 0

    def mock_generator() -> EntityId:
        nonlocal call_count
        call_count += 1
        return EntityId("opp-runtime-1")

    result = validate_opportunity_proposal(
        proposal, candidate_set, state, plot_file, mock_generator
    )

    assert not result.is_valid
    assert call_count == 0
    assert any("not an active current milestone" in d for d in result.diagnostics)


def test_validate_rejects_invalid_entity_ordinal() -> None:
    proposal = _make_proposal(entity_ordinals=[1, 50])
    candidate_set = _make_candidate_set()
    state = _make_state()
    plot_file = _make_plot_file()

    call_count = 0

    def mock_generator() -> EntityId:
        nonlocal call_count
        call_count += 1
        return EntityId("opp-runtime-1")

    result = validate_opportunity_proposal(
        proposal, candidate_set, state, plot_file, mock_generator
    )

    assert not result.is_valid
    assert call_count == 0
    assert any("entity_ordinal 50" in d for d in result.diagnostics)


def test_validate_rejects_duplicate_active_title() -> None:
    existing_opp = OpportunityDefinition(
        id=EntityId("opp-auth-1"),
        parent_milestone_id=EntityId("m_active_1"),
        title=DisplayString("Infiltrate the Cellar"),
        description=DisplayString("Desc"),
        referenced_entity_ids=[],
        allowed_outcome_ids=[EntityId("out_1")],
        preconditions=[],
        expiry_conditions=[],
        balance_rating=50,
    )
    proposal = _make_proposal(title="Infiltrate the Cellar")
    candidate_set = _make_candidate_set()
    state = _make_state()
    plot_file = _make_plot_file(authored_opps=[existing_opp])

    call_count = 0

    def mock_generator() -> EntityId:
        nonlocal call_count
        call_count += 1
        return EntityId("opp-runtime-1")

    result = validate_opportunity_proposal(
        proposal, candidate_set, state, plot_file, mock_generator
    )

    assert not result.is_valid
    assert call_count == 0
    assert any("duplicates existing authored opportunity" in d for d in result.diagnostics)
