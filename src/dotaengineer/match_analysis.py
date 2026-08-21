import argparse
from pathlib import Path
from typing import Any

import gem


STAGING_REPLAYS_DIR = Path("data/staging/replays")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect detailed player data from "
            "a parsed Dota 2 replay."
        )
    )

    parser.add_argument(
        "match_id",
        type=int,
        help="Dota 2 match ID",
    )

    parser.add_argument(
        "player_name",
        type=str,
        help="Player name to inspect",
    )

    return parser.parse_args()


def find_player(
    players: list,
    player_name: str,
):
    normalized_target = player_name.lower()

    # First try exact match
    for player in players:
        if (
            player.player_name
            and player.player_name.lower()
            == normalized_target
        ):
            return player

    # Then try partial match
    for player in players:
        if (
            player.player_name
            and normalized_target
            in player.player_name.lower()
        ):
            return player

    return None


def print_value_summary(
    name: str,
    value: Any,
    preview_items: int = 3,
) -> None:
    print(f"\n--- {name} ---")
    print(f"Type: {type(value).__name__}")

    if value is None:
        print("Value: None")
        return

    if isinstance(value, dict):
        print(f"Entries: {len(value)}")

        for index, (key, item) in enumerate(
            value.items()
        ):
            if index >= preview_items:
                break

            print(
                f"[{index}] "
                f"{key!r} -> {item!r}"
            )

        return

    if isinstance(
        value,
        (list, tuple),
    ):
        print(f"Entries: {len(value)}")

        for index, item in enumerate(
            value[:preview_items]
        ):
            print(
                f"[{index}] {item!r}"
            )

        return

    print(f"Value: {value!r}")


def print_player_summary(player) -> None:
    print("\n" + "=" * 60)
    print("PLAYER SUMMARY")
    print("=" * 60)

    fields = [
        "player_name",
        "account_id",
        "steam_id",
        "hero_name",
        "team",
        "is_radiant",
        "win",
        "kills",
        "deaths",
        "assists",
        "kda",
        "last_hits",
        "denies",
        "net_worth",
        "level",
        "hero_damage",
        "hero_healing",
        "tower_damage",
        "teamfight_participation",
        "lane_role",
        "lane_efficiency_pct",
        "buyback_count",
        "rune_pickups",
        "obs_placed",
        "sen_placed",
    ]

    for field in fields:
        value = getattr(
            player,
            field,
            None,
        )

        print(
            f"{field:28} "
            f"{value}"
        )


def inspect_player_logs(player) -> None:
    fields_to_inspect = [
        "kills_log",
        "damage_targets",
        "damage_inflictor",
        "damage_inflictor_received",
        "damage_taken",
        "purchase_log",
        "buyback_log",
        "runes_log",
        "position_log",
        "gold_t",
        "xp_t",
        "net_worth_t",
        "lh_t",
        "dn_t",
        "ability_uses",
        "ability_targets",
        "item_uses",
    ]

    print("\n" + "=" * 60)
    print("PLAYER DATA STRUCTURES")
    print("=" * 60)

    for field in fields_to_inspect:
        value = getattr(
            player,
            field,
            None,
        )

        print_value_summary(
            field,
            value,
        )


def inspect_match_context(match) -> None:
    print("\n" + "=" * 60)
    print("MATCH CONTEXT")
    print("=" * 60)

    print(
        f"Match ID: "
        f"{match.match_id}"
    )

    print(
        f"Duration: "
        f"{match.duration_minutes:.2f} min"
    )

    print(
        f"Radiant: "
        f"{match.radiant_team_name}"
    )

    print(
        f"Dire: "
        f"{match.dire_team_name}"
    )

    print(
        f"Score: "
        f"{match.radiant_score}"
        f" - "
        f"{match.dire_score}"
    )

    print(
        f"Radiant win: "
        f"{match.radiant_win}"
    )

    print_value_summary(
        "teamfights",
        match.teamfights,
    )

    print_value_summary(
        "opendota_teamfights",
        match.opendota_teamfights,
    )

    print_value_summary(
        "combat_log",
        match.combat_log,
    )

    print_value_summary(
        "roshans",
        match.roshans,
    )

    print_value_summary(
        "objectives",
        match.objectives,
    )


def main() -> None:
    args = parse_arguments()

    match_id = args.match_id
    player_name = args.player_name

    replay_path = (
        STAGING_REPLAYS_DIR
        / f"{match_id}.dem"
    )

    if not replay_path.exists():
        raise FileNotFoundError(
            f"Replay not found: "
            f"{replay_path}"
        )

    print(
        f"Parsing replay: "
        f"{replay_path}"
    )

    match = gem.parse(
        replay_path
    )

    if match.match_id != match_id:
        raise ValueError(
            "Replay match ID mismatch. "
            f"Expected {match_id}, "
            f"got {match.match_id}"
        )

    

    

    player = find_player(
        match.players,
        player_name,
    )

    if player is None:
        print(
            f"\nPlayer '{player_name}' "
            f"was not found."
        )

        print(
            "\nAvailable players:"
        )

        for item in match.players:
            print(
                f"- {item.player_name}"
            )

        return

    print("\n--- Time series validation ---")
    for name in [
            "gold_t",
            "xp_t",
            "net_worth_t",
        ]:
            values = getattr(player, name)
    
            print(f"\n{name}")
            print(f"Entries: {len(values)}")
            print(f"Min: {min(values)}")
            print(f"Max: {max(values)}")
            print(f"First: {values[0]}")
            print(f"Middle: {values[len(values) // 2]}")
            print(f"Last: {values[-1]}")

    print("\n--- Time series synchronization ---")

    sample_indexes = [
        0,
        len(player.net_worth_t) // 4,
        len(player.net_worth_t) // 2,
        (len(player.net_worth_t) * 3) // 4,
        len(player.net_worth_t) - 1,
    ]

    for index in sample_indexes:
        tick, x, y = player.position_log[index]

        print(
            f"\nIndex: {index}"
            f"\nTick: {tick}"
            f"\nPosition: ({x:.2f}, {y:.2f})"
            f"\nNet worth: {player.net_worth_t[index]}"
            f"\nXP: {player.xp_t[index]}"
        )


    print("\n--- Tick / game time validation ---")

    print(f"Game start tick: {match.game_start_tick}")
    print(f"Game end tick:   {match.game_end_tick}")
    print(f"Duration seconds: {match.duration_seconds:.2f}")

    tick_span = match.game_end_tick - match.game_start_tick

    print(f"Game tick span: {tick_span}")

    if match.duration_seconds > 0:
        estimated_ticks_per_second = (
            tick_span / match.duration_seconds
        )

        print(
            f"Estimated ticks/second: "
            f"{estimated_ticks_per_second:.4f}"
        )

    print("\nSample positions relative to game start:")

    sample_indexes = [
        0,
        len(player.position_log) // 4,
        len(player.position_log) // 2,
        (len(player.position_log) * 3) // 4,
        len(player.position_log) - 1,
    ]

    for index in sample_indexes:
        tick, x, y = player.position_log[index]

        relative_tick = tick - match.game_start_tick

        print(
            f"\nIndex: {index}"
            f"\nTick: {tick}"
            f"\nRelative tick: {relative_tick}"
            f"\nPosition: ({x:.2f}, {y:.2f})"
            f"\nNet worth: {player.net_worth_t[index]}"
            f"\nXP: {player.xp_t[index]}"
        )



    inspect_match_context(
        match
    )

    print_player_summary(
        player
    )

    inspect_player_logs(
        player
    )


if __name__ == "__main__":
    main()