"""Unit tests for COMBAT-07 combat flee and yield transitions."""

import datetime

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.models.player_state import PlayerState
from domain.models.runtime_common import ResourceValue
from domain.models.world_state import LocationState
from engine.combat.consequences import AuthoredConsequence, apply_player_consequences
from engine.combat.escape import (
    EscapePolicyDefinition,
    YieldPolicyDefinition,
    execute_flee_command,
    execute_yield_command,
)
from engine.dice.checks import ExplorationBand
from engine.dice.service import DiceService
from engine.dice.testing import ScriptedRandomSource


def make_test_combat() -> CombatState:
    hero = CombatParticipant(
        hp=ResourceValue(current=20, maximum=20),
        armour=ResourceValue(current=5, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        statuses=[],
        side=ParticipantSide.PARTY,
    )
    enemy = CombatParticipant(
        hp=ResourceValue(current=15, maximum=15),
        armour=ResourceValue(current=2, maximum=2),
        mana=ResourceValue(current=0, maximum=0),
        statuses=[],
        side=ParticipantSide.ENEMY,
    )
    return CombatState(
        encounter_id=EntityId("enc_1"),
        phase=CombatPhase.ACTIVE,
        round=1,
        order=[EntityId("hero"), EntityId("enemy")],
        current_index=0,
        participants={
            EntityId("hero"): hero,
            EntityId("enemy"): enemy,
        },
    )


def make_escape_policy() -> EscapePolicyDefinition:
    return EscapePolicyDefinition(
        id=EntityId("esc_woods"),
        dc=12,
        consequences={
            ExplorationBand.CRITICAL_SUCCESS: AuthoredConsequence(
                consequence_id=EntityId("clean_escape"),
                kind="escape",
                description=DisplayString("You slipped away undetected into the dense fog."),
                world_flags={EntityId("escaped_woods"): True},
            ),
            ExplorationBand.SUCCESS: AuthoredConsequence(
                consequence_id=EntityId("flee_success"),
                kind="escape",
                description=DisplayString("You broke away and escaped back to the trail."),
                world_flags={EntityId("escaped_woods"): True},
            ),
            ExplorationBand.PARTIAL_SUCCESS: AuthoredConsequence(
                consequence_id=EntityId("flee_partial"),
                kind="escape_with_scrapes",
                description=DisplayString("You scrambled away through thorn bushes, losing 2 HP."),
                hp_loss=2,
                world_flags={EntityId("escaped_woods"): True},
            ),
            ExplorationBand.FAILURE: AuthoredConsequence(
                consequence_id=EntityId("flee_fail"),
                kind="blocked",
                description=DisplayString("The beast cut off your retreat!"),
            ),
            ExplorationBand.CRITICAL_FAILURE: AuthoredConsequence(
                consequence_id=EntityId("flee_crit_fail"),
                kind="ambushed",
                description=DisplayString("You tripped and fell, exposed to enemy assault!"),
                hp_loss=3,
            ),
        },
    )


def make_dice_service(rolls: list[int]) -> DiceService:
    rng = ScriptedRandomSource(rolls)

    def clock() -> datetime.datetime:
        return datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)

    def id_gen() -> EntityId:
        return EntityId("roll_1")

    return DiceService(rng=rng, clock=clock, id_generator=id_gen)


def test_flee_success_ends_combat() -> None:
    combat = make_test_combat()
    policy = make_escape_policy()
    dice_service = make_dice_service([15])  # 15 vs DC 12 -> Success

    res = execute_flee_command(
        combat=combat,
        actor_id=EntityId("hero"),
        escape_policy=policy,
        dice_service=dice_service,
        difficulty=DefaultDifficulty.NORMAL,
    )

    assert res.success
    assert res.combat_ended
    assert res.band == ExplorationBand.SUCCESS
    assert res.consequence_applied is not None
    assert res.consequence_applied.world_flags[EntityId("escaped_woods")] is True


def test_flee_failure_keeps_combat_active() -> None:
    combat = make_test_combat()
    policy = make_escape_policy()
    dice_service = make_dice_service([4])  # 4 vs DC 12 -> Failure

    res = execute_flee_command(
        combat=combat,
        actor_id=EntityId("hero"),
        escape_policy=policy,
        dice_service=dice_service,
        difficulty=DefaultDifficulty.NORMAL,
    )

    assert not res.success
    assert not res.combat_ended
    assert res.band == ExplorationBand.FAILURE
    assert res.updated_combat is not None


def test_flee_difficulty_dc_scaling() -> None:
    combat = make_test_combat()
    policy = make_escape_policy()  # Base DC 12

    # Hard difficulty (+2 DC -> DC 14): roll 10 is a Failure (10 < 14 - 3 = 11)
    dice_hard = make_dice_service([10])
    res_hard = execute_flee_command(
        combat=combat,
        actor_id=EntityId("hero"),
        escape_policy=policy,
        dice_service=dice_hard,
        difficulty=DefaultDifficulty.HARD,
    )
    assert res_hard.band == ExplorationBand.FAILURE

    # Story difficulty (-2 DC -> DC 10): roll 10 is a Success (10 >= 10)
    dice_story = make_dice_service([10])
    res_story = execute_flee_command(
        combat=combat,
        actor_id=EntityId("hero"),
        escape_policy=policy,
        dice_service=dice_story,
        difficulty=DefaultDifficulty.STORY,
    )
    assert res_story.band == ExplorationBand.SUCCESS


def test_yield_allowed_ends_combat_without_roll() -> None:
    combat = make_test_combat()
    yield_policy = YieldPolicyDefinition(
        id=EntityId("yield_guards"),
        allowed=True,
        consequence=AuthoredConsequence(
            consequence_id=EntityId("captured"),
            kind="capture",
            description=DisplayString("You laid down your arms and were escorted to the dungeon."),
            relocation_area_id=EntityId("dungeon_cell"),
        ),
    )

    res = execute_yield_command(combat, EntityId("hero"), yield_policy)
    assert res.success
    assert res.combat_ended
    assert res.consequence_applied.relocation_area_id == EntityId("dungeon_cell")


def test_yield_denied_raises_error() -> None:
    combat = make_test_combat()
    yield_policy = YieldPolicyDefinition(
        id=EntityId("yield_boss"),
        allowed=False,
        consequence=AuthoredConsequence(
            consequence_id=EntityId("no_quarter"),
            kind="death",
            description=DisplayString("The warlord grants no quarter."),
        ),
    )

    with pytest.raises(ValueError, match="Yielding is not permitted"):
        execute_yield_command(combat, EntityId("hero"), yield_policy)


def test_apply_player_consequences_bounds() -> None:
    player = PlayerState(
        id=EntityId("hero"),
        name=DisplayString("Hero"),
        background_id=EntityId("bg_hero"),
        stats=StatBlock(
            strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10
        ),
        hp=ResourceValue(current=5, maximum=20),
        armour=ResourceValue(current=5, maximum=5),
        mana=ResourceValue(current=3, maximum=10),
        mana_regen=2,
        speed=10,
        luck_capacity=3,
    )
    location = LocationState(area_id=EntityId("forest"))
    flags: dict[EntityId, bool | int | str] = {}

    consequence = AuthoredConsequence(
        consequence_id=EntityId("heavy_loss"),
        kind="loss",
        description=DisplayString("Heavy loss"),
        hp_loss=10,  # 5 - 10 -> should floor at 1 HP
        mana_loss=5,  # 3 - 5 -> should floor at 0 mana
        relocation_area_id=EntityId("temple"),
        world_flags={EntityId("survived_near_death"): True},
    )

    new_p, new_loc, new_flags, _logs = apply_player_consequences(
        player, location, flags, consequence
    )
    assert new_p.hp.current == 1  # HP bounded at 1
    assert new_p.mana.current == 0  # Mana bounded at 0
    assert new_loc.area_id == EntityId("temple")
    assert new_flags[EntityId("survived_near_death")] is True
