"""Campaign file validation."""

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from domain.models.area import AreasFile
from domain.models.balance import BalanceFile
from domain.models.campaign_meta import CampaignMeta
from domain.models.character import CharactersFile
from domain.models.diagnostics import Diagnostic
from domain.models.enemy import EnemiesFile
from domain.models.item import ItemsFile
from domain.models.pack import CampaignPack
from domain.models.plot import PlotFile
from domain.models.skill import SkillsFile
from domain.models.style_bible import StyleBibleFile
from domain.models.world import WorldFile

REQUIRED_FILES = {
    "campaign.json": CampaignMeta,
    "style.json": StyleBibleFile,
    "world.json": WorldFile,
    "areas.json": AreasFile,
    "characters.json": CharactersFile,
    "skills.json": SkillsFile,
    "items.json": ItemsFile,
    "enemies.json": EnemiesFile,
    "plot.json": PlotFile,
    "balance.json": BalanceFile,
}


def validate_campaign_files(
    file_contents: Mapping[str, Any],
) -> tuple[CampaignPack | None, list[Diagnostic]]:
    """Validate already-decoded file contents and return pack or diagnostics."""
    diagnostics: list[Diagnostic] = []

    expected_names = set(REQUIRED_FILES.keys())
    provided_names = set(file_contents.keys())

    missing = expected_names - provided_names
    extra = provided_names - expected_names

    for name in missing:
        diagnostics.append(
            Diagnostic(
                code="file_missing",
                file=name,
                json_pointer="/",
                message=f"Missing required campaign file: {name}",
            )
        )

    for name in extra:
        diagnostics.append(
            Diagnostic(
                code="file_extra",
                file=name,
                json_pointer="/",
                message=f"Unexpected campaign file: {name}",
            )
        )

    if missing or extra:
        return None, sorted(diagnostics)

    parsed_models: dict[str, Any] = {}

    for filename, model_cls in REQUIRED_FILES.items():
        data = file_contents[filename]
        if not isinstance(data, dict):
            diagnostics.append(
                Diagnostic(
                    code="type_error",
                    file=filename,
                    json_pointer="/",
                    message="Root must be a JSON object",
                )
            )
            continue

        try:
            parsed_models[filename] = model_cls(**data)
        except ValidationError as exc:
            for err in exc.errors():
                loc = "/" + "/".join(str(x) for x in err["loc"])
                diagnostics.append(
                    Diagnostic(
                        code=err["type"],
                        file=filename,
                        json_pointer=loc,
                        message=err["msg"],
                    )
                )

    if diagnostics:
        return None, sorted(diagnostics)

    campaign_meta: CampaignMeta = parsed_models["campaign.json"]
    expected_id = campaign_meta.campaign_id
    expected_version = campaign_meta.campaign_version

    for filename, model in parsed_models.items():
        if filename == "campaign.json":
            continue

        if getattr(model, "campaign_id", None) != expected_id:
            diagnostics.append(
                Diagnostic(
                    code="mismatched_campaign_id",
                    file=filename,
                    json_pointer="/campaign_id",
                    message=f"Expected campaign_id {expected_id}",
                )
            )

        if getattr(model, "campaign_version", None) != expected_version:
            diagnostics.append(
                Diagnostic(
                    code="mismatched_campaign_version",
                    file=filename,
                    json_pointer="/campaign_version",
                    message=f"Expected campaign_version {expected_version}",
                )
            )

    if diagnostics:
        return None, sorted(diagnostics)

    pack = CampaignPack(
        meta=parsed_models["campaign.json"],
        style=parsed_models["style.json"],
        world=parsed_models["world.json"],
        areas=parsed_models["areas.json"],
        characters=parsed_models["characters.json"],
        skills=parsed_models["skills.json"],
        items=parsed_models["items.json"],
        enemies=parsed_models["enemies.json"],
        plot=parsed_models["plot.json"],
        balance=parsed_models["balance.json"],
    )

    return pack, []
