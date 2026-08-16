"""Unit tests for OpportunityPlannerAdapter and opportunity prompt pipeline (LLM-08)."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.common import DisplayString, EntityId
from domain.models.pack import CampaignPack
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import MilestoneState, PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState
from engine.campaign import load_campaign
from engine.plot.proposal_validator import OpportunityCandidateSet
from llm.ollama_client import OllamaClient
from llm.orchestration.opportunity_planner import OpportunityPlannerAdapter


@pytest.fixture
def minimal_pack() -> CampaignPack:
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "campaigns" / "valid-minimal"
    pack, _ = load_campaign(fixture_path)
    assert pack is not None
    return pack


@pytest.fixture
def sample_plot_state() -> RuntimeState:
    player = PlayerState(
        id="player-1",
        name="Hero",
        background_id="bg-1",
        stats=StatBlock(
            strength=10,
            dexterity=10,
            intelligence=10,
            charisma=10,
            constitution=10,
            wisdom=10,
        ),
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=5, maximum=5),
        mana_regen=1,
        speed=30,
        luck_capacity=3,
    )
    return RuntimeState(
        schema_version=1,
        save_id="save-1",
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        campaign_fingerprint="fp-123",
        difficulty=DefaultDifficulty.NORMAL,
        revision=1,
        player=player,
        party=PartyState(protagonist_id="player-1"),
        location=LocationState(area_id="area-1", discovered_area_ids={"area-1"}),
        plot=PlotState(
            milestones={"milestone-1": MilestoneState.ACTIVE},
            current_milestone_ids={"milestone-1"},
        ),
        known_fact_ids={"fact-1"},
    )


@pytest.fixture
def sample_candidate_set() -> OpportunityCandidateSet:
    return OpportunityCandidateSet(
        milestones=[EntityId("milestone-1")],
        entities=[EntityId("resident-1"), EntityId("object-1")],
        outcomes=[EntityId("milestone-1")],
        predicates=[DisplayString("milestone:milestone-1:active")],
    )


def _valid_opp_dict(
    parent_ord: int = 1,
    title: str = "Unique Crypt Rumor",
    canonical_claims: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "request_id": "opp-req-1",
        "parent_milestone_ordinal": parent_ord,
        "title": title,
        "description": "Examine the strange symbols found in the crypt.",
        "entity_ordinals": [1],
        "approach_tags": ["investigation"],
        "allowed_outcome_ordinals": [1],
        "precondition_ordinals": [1],
        "expiry_condition_ordinals": [1],
        "challenge_label": "standard",
        "pacing_reason": "Provide tactical engagement.",
        "canonical_claims": canonical_claims or [],
        "balance_rating": 50,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_propose_opportunity_success_first_attempt(
    sample_plot_state: RuntimeState,
    minimal_pack: CampaignPack,
    sample_candidate_set: OpportunityCandidateSet,
) -> None:
    id_count = 0

    def gen_id() -> EntityId:
        nonlocal id_count
        id_count += 1
        return EntityId(f"opp-gen-{id_count}")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": json.dumps(_valid_opp_dict())}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    adapter = OpportunityPlannerAdapter(ollama_client=client)

    result = await adapter.propose_opportunity(
        state=sample_plot_state,
        pack=minimal_pack,
        candidate_set=sample_candidate_set,
        id_generator=gen_id,
    )

    assert result.is_valid is True
    assert result.opportunity_def is not None
    assert result.opportunity_def.id == "opp-gen-1"
    assert result.opportunity_def.title == "Unique Crypt Rumor"
    assert id_count == 1


@pytest.mark.anyio
async def test_propose_opportunity_repaired_on_second_attempt(
    sample_plot_state: RuntimeState,
    minimal_pack: CampaignPack,
    sample_candidate_set: OpportunityCandidateSet,
) -> None:
    calls = 0

    def gen_id() -> EntityId:
        return EntityId("opp-repaired-1")

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            # First attempt: invalid JSON
            return httpx.Response(
                status_code=200,
                json={"message": {"role": "assistant", "content": "not json"}},
            )
        # Second attempt: valid
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": json.dumps(_valid_opp_dict())}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    adapter = OpportunityPlannerAdapter(ollama_client=client)

    result = await adapter.propose_opportunity(
        state=sample_plot_state,
        pack=minimal_pack,
        candidate_set=sample_candidate_set,
        id_generator=gen_id,
    )

    assert result.is_valid is True
    assert calls == 2
    assert result.opportunity_def is not None


@pytest.mark.anyio
async def test_propose_opportunity_canonical_claim_rejected(
    sample_plot_state: RuntimeState,
    minimal_pack: CampaignPack,
    sample_candidate_set: OpportunityCandidateSet,
) -> None:
    id_count = 0

    def gen_id() -> EntityId:
        nonlocal id_count
        id_count += 1
        return EntityId("opp-bad")

    def handler(request: httpx.Request) -> httpx.Response:
        bad_dict = _valid_opp_dict(canonical_claims=["The king is secretly an alien"])
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": json.dumps(bad_dict)}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    adapter = OpportunityPlannerAdapter(ollama_client=client)

    result = await adapter.propose_opportunity(
        state=sample_plot_state,
        pack=minimal_pack,
        candidate_set=sample_candidate_set,
        id_generator=gen_id,
    )

    assert result.is_valid is False
    assert id_count == 0  # No ID consumed on rejection
    assert any("canonical claims" in d for d in result.diagnostics)


@pytest.mark.anyio
async def test_propose_opportunity_timeout_returns_invalid_without_crash(
    sample_plot_state: RuntimeState,
    minimal_pack: CampaignPack,
    sample_candidate_set: OpportunityCandidateSet,
) -> None:
    def gen_id() -> EntityId:
        return EntityId("opp-never")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timeout")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    adapter = OpportunityPlannerAdapter(ollama_client=client)

    result = await adapter.propose_opportunity(
        state=sample_plot_state,
        pack=minimal_pack,
        candidate_set=sample_candidate_set,
        id_generator=gen_id,
    )

    assert result.is_valid is False
    assert any("timed out" in d.lower() or "transport" in d.lower() for d in result.diagnostics)
