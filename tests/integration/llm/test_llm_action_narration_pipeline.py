"""End-to-end integration tests for LLM action interpretation, narration, and planner (LLM-09)."""

import json
import shutil
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from campaign.storage.save_reader import SaveReader
from domain.models.common import DisplayString, EntityId
from domain.models.pack import CampaignPack
from domain.models.plot_state import MilestoneState, PlotState
from engine.campaign import load_campaign
from engine.plot.proposal_validator import OpportunityCandidateSet
from llm.contracts.action import ActionProposal
from llm.contracts.narration import NarrationV1
from llm.ollama_client import OllamaClient
from llm.orchestration.action_interpreter import ActionInterpreter
from llm.orchestration.narrator import NarratorOrchestrator
from llm.orchestration.opportunity_planner import OpportunityPlannerAdapter
from llm.prompts.action_interpreter_v1 import ACTION_INTERPRETER_PROMPT_VERSION
from llm.prompts.narrator_v1 import NARRATOR_PROMPT_VERSION


@pytest.fixture
def test_setup(tmp_path: Path) -> tuple[Settings, CampaignPack, str]:
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir(parents=True)

    fixture_src = Path(__file__).parent.parent.parent / "fixtures" / "campaigns" / "valid-minimal"
    target_c_dir = campaigns_dir / "minimal-campaign"
    shutil.copytree(fixture_src, target_c_dir)

    pack, _ = load_campaign(target_c_dir)
    assert pack is not None

    settings = Settings(
        campaigns_dir=str(tmp_path),
        storymode_env="test",
        ollama_base_url="http://127.0.0.1:11434",
    )

    app = create_app(settings)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/saves",
        json={
            "campaign_id": "minimal-campaign",
            "command_id": "cmd-init-pipe",
            "slot_name": "Pipeline Save",
            "slot_kind": "manual",
            "player_name": "Hero",
            "background_id": "bg-1",
            "difficulty": "normal",
            "stats": {
                "strength": 10,
                "dexterity": 12,
                "constitution": 13,
                "intelligence": 15,
                "wisdom": 14,
                "charisma": 8,
            },
        },
    )
    assert resp.status_code == 201
    save_id = str(resp.json()["save_id"])

    return settings, pack, save_id


@pytest.mark.anyio
async def test_full_pipeline_action_submit_and_narrate(
    test_setup: tuple[Settings, CampaignPack, str],
) -> None:
    settings, _pack, save_id = test_setup

    def mock_ollama_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        messages = body.get("messages", [])
        sys_msg = messages[0]["content"] if messages else ""

        if "Action Interpreter" in sys_msg:
            # Action proposal
            proposal = ActionProposal(
                contract_version=1,
                prompt_version=ACTION_INTERPRETER_PROMPT_VERSION,
                request_id="act-cmd-1",
                status="valid",
                operation="investigate",
                verb="search",
                entity_mentions=[],
                capability_mentions=[],
                intended_effect="Search the room for hidden compartments.",
                challenge_label="none",
                uncertainty_reason="Simple search.",
                stakes=["Find clues."],
            )
            return httpx.Response(
                status_code=200,
                json={"message": {"role": "assistant", "content": proposal.model_dump_json()}},
            )
        elif "Narrator" in sys_msg:
            # Narration
            narration = NarrationV1(
                contract_version=1,
                prompt_version=NARRATOR_PROMPT_VERSION,
                request_id="narr-cmd-1",
                narration=(
                    "You carefully run your fingers along the stone walls, searching every crevice."
                ),
                speaker_ordinals_used=[1],
                fact_ordinals_referenced=[],
            )
            return httpx.Response(
                status_code=200,
                json={"message": {"role": "assistant", "content": narration.model_dump_json()}},
            )

        return httpx.Response(status_code=400, text="Unknown prompt")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_ollama_handler))
    ollama_client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)

    interpreter = ActionInterpreter(ollama_client=ollama_client)
    narrator = NarratorOrchestrator(ollama_client=ollama_client)

    app = create_app(settings)
    app.state.action_interpreter = interpreter
    app.state.narrator_orchestrator = narrator

    client = TestClient(app)

    response = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "command_id": "cmd-1",
            "expected_revision": 1,
            "player_text": "I search the room carefully.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["revision"] == 2
    assert "crevice" in data["narration"]


@pytest.mark.anyio
async def test_narrator_fallback_on_model_crash(
    test_setup: tuple[Settings, CampaignPack, str],
) -> None:
    settings, _pack, save_id = test_setup

    def mock_ollama_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        messages = body.get("messages", [])
        sys_msg = messages[0]["content"] if messages else ""

        if "Action Interpreter" in sys_msg:
            proposal = ActionProposal(
                contract_version=1,
                prompt_version=ACTION_INTERPRETER_PROMPT_VERSION,
                request_id="act-cmd-crash",
                status="valid",
                operation="investigate",
                verb="search",
                entity_mentions=[],
                capability_mentions=[],
                intended_effect="Search the room.",
                challenge_label="none",
                uncertainty_reason="Simple search.",
                stakes=[],
            )
            return httpx.Response(
                status_code=200,
                json={"message": {"role": "assistant", "content": proposal.model_dump_json()}},
            )
        # Narrator fails with 500
        return httpx.Response(status_code=500, text="Crash")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_ollama_handler))
    ollama_client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)

    app = create_app(settings)
    app.state.action_interpreter = ActionInterpreter(ollama_client=ollama_client)
    app.state.narrator_orchestrator = NarratorOrchestrator(ollama_client=ollama_client)

    client = TestClient(app)

    response = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "command_id": "cmd-crash",
            "expected_revision": 1,
            "player_text": "I search the room.",
        },
    )

    # The action must succeed (revision 2) and return deterministic fallback narration
    assert response.status_code == 200
    data = response.json()
    assert data["revision"] == 2
    assert data["narration"] == "Action submitted"


@pytest.mark.anyio
async def test_opportunity_planner_integration(
    test_setup: tuple[Settings, CampaignPack, str],
) -> None:
    settings, pack, save_id = test_setup

    reader = SaveReader(Path(settings.campaigns_dir))
    load_res = reader.load_save("minimal-campaign", save_id)
    state = load_res.state
    # Activate milestone-1 in plot state
    state = state.model_copy(
        update={
            "plot": PlotState(
                current_milestone_ids={EntityId("milestone-1")},
                milestones={EntityId("milestone-1"): MilestoneState.ACTIVE},
            )
        }
    )

    candidate_set = OpportunityCandidateSet(
        milestones=[EntityId("milestone-1")],
        entities=[EntityId("resident-1")],
        outcomes=[EntityId("milestone-1")],
        predicates=[DisplayString("milestone:milestone-1:active")],
    )

    def mock_ollama_handler(request: httpx.Request) -> httpx.Response:
        opp_proposal_dict = {
            "schema_version": 1,
            "request_id": "opp-int-1",
            "parent_milestone_ordinal": 1,
            "title": "Discovered Underground Passage",
            "description": "A hidden door behind the bookshelf.",
            "entity_ordinals": [1],
            "approach_tags": ["exploration"],
            "allowed_outcome_ordinals": [1],
            "precondition_ordinals": [],
            "expiry_condition_ordinals": [1],
            "challenge_label": "standard",
            "pacing_reason": "Provide exploration branch.",
            "canonical_claims": [],
            "balance_rating": 50,
        }
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": json.dumps(opp_proposal_dict)}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_ollama_handler))
    ollama_client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    planner = OpportunityPlannerAdapter(ollama_client=ollama_client)

    result = await planner.propose_opportunity(
        state=state,
        pack=pack,
        candidate_set=candidate_set,
        id_generator=lambda: EntityId("opp-dynamic-1"),
        request_id="opp-int-1",
    )

    assert result.is_valid is True
    assert result.opportunity_def is not None
    assert result.opportunity_def.title == "Discovered Underground Passage"


@pytest.mark.anyio
async def test_action_interpreter_timeout_returns_503(
    test_setup: tuple[Settings, CampaignPack, str],
) -> None:
    settings, _pack, save_id = test_setup

    def mock_ollama_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Ollama timed out")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_ollama_handler))
    ollama_client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)

    app = create_app(settings)
    app.state.action_interpreter = ActionInterpreter(ollama_client=ollama_client)

    client = TestClient(app)

    response = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "command_id": "cmd-timeout",
            "expected_revision": 1,
            "player_text": "Search the room.",
        },
    )

    assert response.status_code == 503
    reader = SaveReader(Path(settings.campaigns_dir))
    load_res = reader.load_save("minimal-campaign", save_id)
    # State revision remains 1 (no mutation on failure)
    assert load_res.state.revision == 1


@pytest.mark.anyio
async def test_full_pipeline_check_resolution_and_narration(
    test_setup: tuple[Settings, CampaignPack, str],
) -> None:
    settings, _pack, save_id = test_setup

    def mock_ollama_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        messages = body.get("messages", [])
        sys_msg = messages[0]["content"] if messages else ""

        if "Action Interpreter" in sys_msg:
            # Action proposal that requires a check
            proposal = ActionProposal(
                contract_version=1,
                prompt_version=ACTION_INTERPRETER_PROMPT_VERSION,
                request_id="act-cmd-check-1",
                status="valid",
                operation="investigate",
                verb="pick lock",
                entity_mentions=[],
                capability_mentions=[],
                intended_effect="Pick the reinforced lock.",
                challenge_label="difficult",
                uncertainty_reason="Complex lock mechanism.",
                stakes=["Open the chest or jam the lock."],
            )
            return httpx.Response(
                status_code=200,
                json={"message": {"role": "assistant", "content": proposal.model_dump_json()}},
            )
        elif "Narrator" in sys_msg:
            narration = NarrationV1(
                contract_version=1,
                prompt_version=NARRATOR_PROMPT_VERSION,
                request_id="narr-cmd-resolve-1",
                narration="With a satisfying click, the heavy lock gives way under your tools.",
                speaker_ordinals_used=[1],
                fact_ordinals_referenced=[],
            )
            return httpx.Response(
                status_code=200,
                json={"message": {"role": "assistant", "content": narration.model_dump_json()}},
            )

        return httpx.Response(status_code=400, text="Unknown prompt")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_ollama_handler))
    ollama_client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)

    app = create_app(settings)
    app.state.action_interpreter = ActionInterpreter(ollama_client=ollama_client)
    app.state.narrator_orchestrator = NarratorOrchestrator(ollama_client=ollama_client)

    client = TestClient(app)

    # 1. Submit action requiring check
    submit_resp = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "command_id": "cmd-check-1",
            "expected_revision": 1,
            "player_text": "I try to pick the heavy lock.",
        },
    )
    assert submit_resp.status_code == 200
    submit_data = submit_resp.json()
    assert submit_data["has_pending_check"] is True
    assert submit_data["revision"] == 2

    # 2. Resolve check
    resolve_resp = client.post(
        "/api/v1/actions/resolve-check",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "command_id": "cmd-resolve-1",
            "expected_revision": 2,
            "use_luck": False,
        },
    )
    assert resolve_resp.status_code == 200
    resolve_data = resolve_resp.json()
    assert resolve_data["revision"] == 3
    assert "click" in resolve_data["narration"]
