#!/usr/bin/env python3
"""Generate JSON schemas for all campaign files."""

import json
import sys
from pathlib import Path

# Ensure src is in sys.path when script is executed directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pydantic import BaseModel

from domain.models.area import AreasFile
from domain.models.balance import BalanceFile
from domain.models.campaign_meta import CampaignMeta
from domain.models.character import CharactersFile
from domain.models.enemy import EnemiesFile
from domain.models.item import ItemsFile
from domain.models.pack import CampaignPack
from domain.models.plot import PlotFile
from domain.models.skill import SkillsFile
from domain.models.style_bible import StyleBibleFile
from domain.models.world import WorldFile

MODELS: dict[str, type[BaseModel]] = {
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
    "pack.json": CampaignPack,
}


def main() -> None:
    schemas_dir = Path("schemas")
    schemas_dir.mkdir(exist_ok=True)

    for filename, model in MODELS.items():
        schema_path = schemas_dir / filename
        schema = model.model_json_schema()
        with schema_path.open("w") as f:
            json.dump(schema, f, indent=2)
            f.write("\n")

    print(f"Generated {len(MODELS)} schemas in {schemas_dir}/")


if __name__ == "__main__":
    main()
