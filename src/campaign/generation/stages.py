"""Individual campaign stage executors with bounded repair (BUILD-06).

Guarantees:
- Executes typed generation prompts against local Ollama client.
- Bounded repair: up to 2 repair attempts per stage on schema or parsing errors.
- Never regenerates valid prior stages; records structured diagnostics.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from campaign.builder.models import (
    DraftStage,
    DraftStageState,
    DraftState,
    StageDiagnostic,
)
from campaign.storage.drafts import DraftRepository
from llm.ollama_client import ChatMessage, ChatOptions, OllamaClient
from llm.prompts.campaign_generation_v1 import (
    render_stage_repair_prompt,
)

MAX_STAGE_REPAIR_ATTEMPTS: int = 2


class StageExecutionError(Exception):
    """Raised when a generation stage fails or exhausts repair attempts."""


def schema_constraint_hints(contract_cls: type[BaseModel]) -> str:
    """List every enum, length, range, and item-count bound in a contract, one per line.

    Stage prompts show the JSON shape but not the limits; live runs showed local models
    overshooting 120-char fields three attempts in a row. This is appended verbatim to
    the generation and repair prompts so the bounds are stated, not discovered.
    """
    schema = contract_cls.model_json_schema()
    defs: dict[str, Any] = schema.get("$defs", {})
    lines: list[str] = []

    def resolve(node: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in node:
            target: dict[str, Any] = defs[node["$ref"].rsplit("/", 1)[-1]]
            return target
        for option in node.get("anyOf", []):
            if option.get("type") != "null":
                return resolve(option)
        return node

    def walk(node: dict[str, Any], path: str) -> None:
        node = resolve(node)
        parts: list[str] = []
        if "enum" in node:
            parts.append("one of " + "|".join(str(v) for v in node["enum"]))
        if "maxLength" in node:
            parts.append(f"string, {node.get('minLength', 0)}-{node['maxLength']} chars")
        if "minimum" in node or "maximum" in node:
            parts.append(f"integer {node.get('minimum', '')}..{node.get('maximum', '')}")
        if "minItems" in node or "maxItems" in node:
            parts.append(f"list, {node.get('minItems', 0)}-{node.get('maxItems', 'n')} items")
        if parts and path:
            line = f"{path}: {'; '.join(parts)}"
            if line not in lines:
                lines.append(line)
        for name, prop in node.get("properties", {}).items():
            walk(prop, f"{path}.{name}" if path else name)
        if "items" in node:
            walk(node["items"], f"{path}[]")
        if isinstance(node.get("additionalProperties"), dict):
            walk(node["additionalProperties"], f"{path}.*")

    walk(schema, "")
    return "\n".join(lines)


def schema_skeleton(contract_cls: type[BaseModel]) -> str:
    """Render an example JSON document with placeholders straight from the contract schema.

    Replaces hand-written shape examples in the stage prompts, which had drifted from the
    Pydantic models until no stage after the first could validate.
    """
    schema = contract_cls.model_json_schema()
    defs: dict[str, Any] = schema.get("$defs", {})

    def build(node: dict[str, Any], name: str, depth: int) -> Any:
        if "$ref" in node:
            return build(defs[node["$ref"].rsplit("/", 1)[-1]], name, depth)
        options = node.get("anyOf", [])
        if options:
            nullable = any(o.get("type") == "null" for o in options)
            real = next(o for o in options if o.get("type") != "null")
            resolved = defs[real["$ref"].rsplit("/", 1)[-1]] if "$ref" in real else real
            # Optional scalars render as null so models write null, not "" (seen live).
            if nullable and resolved.get("type") not in ("object", "array"):
                return None
            return build(real, name, depth)
        if "const" in node:
            return node["const"]
        if "enum" in node:
            return node["enum"][0]
        kind = node.get("type")
        if kind == "object":
            if "properties" in node:
                return {k: build(v, k, depth + 1) for k, v in node["properties"].items()}
            extra = node.get("additionalProperties")
            return {"<key>": build(extra, name, depth + 1)} if isinstance(extra, dict) else {}
        if kind == "array":
            return [build(node["items"], name, depth + 1)] if "items" in node else []
        if kind == "integer":
            return node.get("minimum", 1)
        if kind == "number":
            return node.get("minimum", 1)
        if kind == "boolean":
            return False
        return f"<{name}>"

    return json.dumps(build(schema, "root", 0), indent=1)


def coerce_to_contract_schema(data: Any, contract_cls: type[BaseModel]) -> Any:
    """Best-effort normalization of small-model stage output before strict validation.

    Local models routinely drop a required list field or emit a scalar where a list is
    expected (live runs stalled at stage 2 when a faction omitted `relationship_edges`).
    Using the contract's own JSON schema, this walks the data and, for every array-typed
    field, fills a missing/null one with `[]` and wraps a scalar into a one-element list.
    Only arrays are touched — missing scalars/objects still fail validation, and the caller
    still validates strictly afterward, so this never fabricates content beyond empty lists.
    """
    schema = contract_cls.model_json_schema()
    defs: dict[str, Any] = schema.get("$defs", {})

    def resolve(node: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in node:
            target: dict[str, Any] = defs[node["$ref"].rsplit("/", 1)[-1]]
            return target
        for option in node.get("anyOf", []):
            if option.get("type") != "null":
                return resolve(option)
        return node

    def walk(node: dict[str, Any], value: Any) -> None:
        node = resolve(node)
        kind = node.get("type")
        if kind == "object" and isinstance(value, dict):
            for name, prop in node.get("properties", {}).items():
                if resolve(prop).get("type") == "array":
                    if value.get(name) is None:
                        value[name] = []
                    elif not isinstance(value[name], list):
                        value[name] = [value[name]]
                if name in value:
                    walk(prop, value[name])
        elif kind == "array" and isinstance(value, list) and "items" in node:
            for item in value:
                walk(node["items"], item)

    walk(schema, data)
    return data


def normalize_stage_semantics(data: Any, contract_cls: type[BaseModel]) -> None:
    """Best-effort fixes for common small-model cross-field mistakes, in place.

    Unlike the schema-driven list coercion, these target specific contract invariants that
    local models violate. Each fix is conservative: it removes an invented reference rather
    than fabricating content, so the strict validation that follows still governs.
    """
    if contract_cls.__name__ != "CharactersStageResponse":
        return
    if not isinstance(data, dict):
        return
    characters = data.get("characters")
    companions = characters.get("companions") if isinstance(characters, dict) else None
    if not isinstance(companions, list):
        return
    for comp in companions:
        if not isinstance(comp, dict):
            continue
        # A companion's starting_loadout must be a subset of its starting_skill_ids; models
        # routinely list a loadout skill they never added to known skills. Drop the strays.
        known = set(comp.get("starting_skill_ids") or [])
        loadout = comp.get("starting_loadout")
        if isinstance(loadout, list):
            comp["starting_loadout"] = [s for s in loadout if s in known]


def artifact_id_index(draft: DraftState) -> str:
    """List every `id` defined by valid stages, and ids referenced but not yet defined."""
    defined: dict[str, str] = {}
    referenced: set[str] = set()

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key in ("id", "style_id"):
                if isinstance(node.get(key), str):
                    defined[node[key]] = f"{path} {node.get('name', '')}".strip()
            for key, value in node.items():
                if key in ("id", "style_id", "campaign_id", "request_id"):
                    continue
                if key.endswith("_id") and isinstance(value, str):
                    referenced.add(value)
                elif key.endswith("_ids") and isinstance(value, list):
                    referenced.update(v for v in value if isinstance(v, str))
                walk(value, key if isinstance(value, list) else path)
        elif isinstance(node, list):
            for item in node:
                walk(item, path)

    for name, state in draft.stages.items():
        if state.status == "valid" and state.artifact_data:
            walk(state.artifact_data, name)

    lines = [f"{eid}: {where}" for eid, where in sorted(defined.items())]
    missing = sorted(referenced - set(defined) - {"escape-default"})
    if missing:
        lines.append("Referenced but not yet defined (define these exactly): " + ", ".join(missing))
    return "\n".join(lines) if lines else "(none yet)"


class StageRunner:
    """Executes and repairs individual campaign generation stages."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        draft_repo: DraftRepository,
        model_name: str = "llama3.1:8b",
    ) -> None:
        self.ollama_client = ollama_client
        self.draft_repo = draft_repo
        self.model_name = model_name

    async def execute_stage(
        self,
        stage: DraftStage,
        draft: DraftState,
        contract_cls: type[BaseModel],
        prompt_generator: Callable[[], str],
        context_summary: str,
    ) -> DraftState:
        """Execute a generation stage with up to 2 repair attempts on failure."""
        current_state = draft.stages.get(
            stage, DraftStageState(stage=stage, status="running", attempts=0)
        )
        if current_state.status == "valid":
            return draft

        # Mark stage running
        running_stages = dict(draft.stages)
        running_stages[stage] = current_state.model_copy(
            update={"status": "running", "attempts": current_state.attempts + 1}
        )
        updated_draft = self.draft_repo.save_draft(
            draft.model_copy(update={"stages": running_stages}),
            expected_revision=draft.revision,
        )

        attempts = 0
        skeleton = schema_skeleton(contract_cls)
        meta_stage = updated_draft.stages.get("meta_style")
        if meta_stage and meta_stage.artifact_data:
            meta = meta_stage.artifact_data.get("meta", {})
            skeleton = skeleton.replace("<campaign_id>", str(meta.get("campaign_id", ""))).replace(
                "<campaign_version>", str(meta.get("campaign_version", ""))
            )
        limits = (
            "\n\nRequired JSON shape (placeholders in angle brackets; keep every key):\n"
            + skeleton
            + "\n\nEvery string value is at most 100 characters: a short concrete phrase, "
            "never a paragraph. Lists hold 1-6 items.\n"
            + "\n\nHard field limits (violations are rejected):\n"
            + schema_constraint_hints(contract_cls)
            + "\n\nIDs defined by earlier stages:\n"
            + artifact_id_index(updated_draft)
        )
        prompt = prompt_generator() + limits
        # Bound generation length. The skeleton shows ONE item per list; a real stage expands
        # every list, so scale above the skeleton — but cap so a slow local model finishes
        # within the request timeout. The largest legitimate stage (skills) is ~8k tokens; at
        # ~6-7 tok/s an 8192 cap stays under a 30-min timeout, whereas a higher cap let the
        # model ramble to ~40k chars and time out mid-JSON.
        # ponytail: tune the multiplier/cap if a legitimately large stage is ever truncated.
        num_predict = max(4096, min(8192, len(skeleton) * 6))
        last_raw_response = ""
        last_diagnostics: list[str] = []

        while attempts <= MAX_STAGE_REPAIR_ATTEMPTS:
            attempts += 1
            try:
                chat_res = await self.ollama_client.chat(
                    model=self.model_name,
                    messages=[ChatMessage(role="user", content=prompt)],
                    format_json=True,
                    # Skeleton + limits + id index + brief plus a long JSON reply need a wide
                    # window; 24k leaves room for prompt + num_predict without truncation.
                    options=ChatOptions(num_ctx=24576, num_predict=num_predict),
                )
                last_raw_response = chat_res.message.content

                # Best-effort normalize small-model quirks (dropped/scalarized lists), then
                # validate strictly against the stage contract. Re-serialize so validation
                # keeps model_validate_json's lax JSON coercion (e.g. enum strings).
                parsed = json.loads(last_raw_response)
                if isinstance(parsed, dict):
                    coerce_to_contract_schema(parsed, contract_cls)
                    normalize_stage_semantics(parsed, contract_cls)
                validated = contract_cls.model_validate_json(json.dumps(parsed))

                # Success!
                stage_data: dict[str, Any] = validated.model_dump(mode="json")
                stage_result = DraftStageState(
                    stage=stage,
                    status="valid",
                    attempts=attempts,
                    diagnostics=[],
                    artifact_data=stage_data,
                )
                final_stages = dict(updated_draft.stages)
                final_stages[stage] = stage_result
                return self.draft_repo.save_draft(
                    updated_draft.model_copy(update={"stages": final_stages}),
                    expected_revision=updated_draft.revision,
                )

            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                diag_msg = str(e)
                last_diagnostics.append(diag_msg)
                if attempts <= MAX_STAGE_REPAIR_ATTEMPTS:
                    # Prepare repair prompt
                    prompt = (
                        render_stage_repair_prompt(
                            stage=stage,
                            invalid_json=last_raw_response,
                            diagnostics=[diag_msg],
                            context_summary=context_summary,
                            request_id=f"req-repair-{stage}-{attempts}",
                        )
                        + limits
                    )
            except Exception as e:
                # Fatal transport or network error
                last_diagnostics.append(f"Transport error: {e}")
                break

        # Failed after attempts
        diag_objs = [
            StageDiagnostic(stage=stage, code="STAGE_FAILED", message=d, is_error=True)
            for d in last_diagnostics
        ]
        failed_stage = DraftStageState(
            stage=stage,
            status="invalid",
            attempts=attempts,
            diagnostics=diag_objs,
            artifact_data=None,
        )
        final_stages = dict(updated_draft.stages)
        final_stages[stage] = failed_stage
        return self.draft_repo.save_draft(
            updated_draft.model_copy(update={"stages": final_stages, "diagnostics": diag_objs}),
            expected_revision=updated_draft.revision,
        )
