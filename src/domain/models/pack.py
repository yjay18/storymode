"""Campaign pack aggregation model."""

from domain.models.area import AreasFile
from domain.models.balance import BalanceFile
from domain.models.campaign_meta import CampaignMeta
from domain.models.character import CharactersFile
from domain.models.common import FrozenModel
from domain.models.enemy import EnemiesFile
from domain.models.item import ItemsFile
from domain.models.plot import PlotFile
from domain.models.skill import SkillsFile
from domain.models.style_bible import StyleBibleFile
from domain.models.world import WorldFile


class CampaignPack(FrozenModel):
    """The complete aggregated campaign configuration."""

    meta: CampaignMeta
    style: StyleBibleFile
    world: WorldFile
    areas: AreasFile
    characters: CharactersFile
    skills: SkillsFile
    items: ItemsFile
    enemies: EnemiesFile
    plot: PlotFile
    balance: BalanceFile
