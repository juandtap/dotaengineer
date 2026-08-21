import argparse
from pathlib import Path

import gem
import pandas as pd


STAGING_REPLAYS_DIR = Path("data/staging/replays")

SILVER_MATCH_DIR = Path("data/silver/match")
SILVER_PLAYER_MATCH_DIR = Path("data/silver/player_match")


def build_match_dataframe(match) -> pd.DataFrame:
    row = {
        "match_id": match.match_id,
        "league_id": match.leagueid,
        "duration_seconds": match.duration_seconds,
        "duration_minutes": match.duration_minutes,
        "pre_game_duration": match.pre_game_duration,
        "radiant_team_id": match.radiant_team_id,
        "radiant_team_name": match.radiant_team_name,
        "radiant_team_tag": match.radiant_team_tag,
        "dire_team_id": match.dire_team_id,
        "dire_team_name": match.dire_team_name,
        "dire_team_tag": match.dire_team_tag,
        "radiant_score": match.radiant_score,
        "dire_score": match.dire_score,
        "radiant_win": match.radiant_win,
        "first_blood_time": match.first_blood_time,
        "game_mode": match.game_mode,
        "game_start_tick": match.game_start_tick,
        "game_end_tick": match.game_end_tick,
        "tower_status_radiant": match.tower_status_radiant,
        "tower_status_dire": match.tower_status_dire,
        "barracks_status_radiant": match.barracks_status_radiant,
        "barracks_status_dire": match.barracks_status_dire,
    }

    return pd.DataFrame([row])


def build_player_match_dataframe(match) -> pd.DataFrame:
    rows = []

    for player in match.players:
        rows.append(
            {
                "match_id": match.match_id,
                "player_id": player.player_id,
                "account_id": player.account_id,
                "steam_id": player.steam_id,
                "player_name": player.player_name,
                "team": player.team,
                "is_radiant": player.is_radiant,
                "hero_id": player.hero_id,
                "hero_name": player.hero_name,
                "win": player.win,
                "kills": player.kills,
                "deaths": player.deaths,
                "assists": player.assists,
                "kda": player.kda,
                "last_hits": player.last_hits,
                "denies": player.denies,
                "net_worth": player.net_worth,
                "level": player.level,
                "hero_damage": player.hero_damage,
                "hero_healing": player.hero_healing,
                "tower_damage": player.tower_damage,
                "buyback_count": player.buyback_count,
                "rune_pickups": player.rune_pickups,
                "obs_placed": player.obs_placed,
                "sen_placed": player.sen_placed,
                "lane_role": player.lane_role,
                "lane_efficiency_pct": player.lane_efficiency_pct,
                "teamfight_participation": player.teamfight_participation,
            }
        )

    return pd.DataFrame(rows)


def validate_match(df: pd.DataFrame) -> None:
    if len(df) != 1:
        raise ValueError(
            f"Expected exactly 1 match row, found {len(df)}"
        )

    if df["match_id"].isna().any():
        raise ValueError(
            "Match dataset contains a null match_id."
        )

    if df["radiant_win"].isna().any():
        print(
            "WARNING: radiant_win is null."
        )

    if df["duration_seconds"].isna().any():
        print(
            "WARNING: duration_seconds is null."
        )


def validate_player_match(df: pd.DataFrame) -> None:
    if len(df) != 10:
        raise ValueError(
            f"Expected 10 players, found {len(df)}"
        )

    if df["account_id"].isna().any():
        print(
            "WARNING: Some players have no account_id."
        )

    if df["hero_id"].isna().any():
        raise ValueError(
            "Some players have no hero_id."
        )

    if df["match_id"].isna().any():
        raise ValueError(
            "Some player rows have no match_id."
        )

    unusual_lane_efficiency = df[
        (df["lane_efficiency_pct"] < 0)
        | (df["lane_efficiency_pct"] > 100)
    ]

    if not unusual_lane_efficiency.empty:
        print(
            "\nNOTE: lane_efficiency_pct contains "
            "values outside the 0-100 range:"
        )

        print(
            unusual_lane_efficiency[
                [
                    "player_name",
                    "hero_name",
                    "lane_efficiency_pct",
                ]
            ].to_string(index=False)
        )


def save_match(
    df: pd.DataFrame,
    match_id: int,
) -> Path:
    output_dir = (
        SILVER_MATCH_DIR
        / f"match_id={match_id}"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / "part-00000.parquet"
    )

    df.to_parquet(
        output_path,
        index=False,
    )

    return output_path


def save_player_match(
    df: pd.DataFrame,
    match_id: int,
) -> Path:
    output_dir = (
        SILVER_PLAYER_MATCH_DIR
        / f"match_id={match_id}"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / "part-00000.parquet"
    )

    df.to_parquet(
        output_path,
        index=False,
    )

    return output_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse a Dota 2 replay and "
            "build Silver datasets."
        )
    )

    parser.add_argument(
        "match_id",
        type=int,
        help="Dota 2 match ID",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    match_id = args.match_id

    replay_path = (
        STAGING_REPLAYS_DIR
        / f"{match_id}.dem"
    )

    if not replay_path.exists():
        raise FileNotFoundError(
            f"Replay not found: {replay_path}"
        )

    print(
        f"Parsing replay: {replay_path}"
    )

    parsed_match = gem.parse(
        replay_path
    )

    if parsed_match.match_id != match_id:
        raise ValueError(
            f"Replay match_id mismatch. "
            f"Expected {match_id}, "
            f"got {parsed_match.match_id}"
        )

    print(
        f"Match ID: {parsed_match.match_id}"
    )

    print(
        f"Players found: "
        f"{len(parsed_match.players)}"
    )

    match_df = build_match_dataframe(
        parsed_match
    )

    player_match_df = (
        build_player_match_dataframe(
            parsed_match
        )
    )

    validate_match(
        match_df
    )

    validate_player_match(
        player_match_df
    )

    print("\n--- match ---")
    print(
        match_df.to_string(
            index=False
        )
    )

    print("\n--- player_match ---")
    print(
        player_match_df.to_string(
            index=False
        )
    )

    match_output_path = save_match(
        match_df,
        match_id,
    )

    player_match_output_path = (
        save_player_match(
            player_match_df,
            match_id,
        )
    )

    print("\nSilver datasets saved:")

    print(
        f"match:"
        f"\n{match_output_path}"
    )

    print(
        f"\nplayer_match:"
        f"\n{player_match_output_path}"
    )


if __name__ == "__main__":
    main()