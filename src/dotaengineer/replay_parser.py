import argparse
from pathlib import Path

import gem
import pandas as pd


STAGING_REPLAYS_DIR = Path("data/staging/replays")
SILVER_PLAYER_MATCH_DIR = Path("data/silver/player_match")


def build_player_match_dataframe(match) -> pd.DataFrame:
    rows = []

    for player in match.players:
        rows.append(
            {
                "match_id": match.match_id,
                "player_id": player.player_id,
                "account_id": player.account_id,
                "player_name": player.player_name,
                "team": player.team,
                "is_radiant": player.is_radiant,
                "hero_id": player.hero_id,
                "hero_name": player.hero_name,
                "kills": player.kills,
                "deaths": player.deaths,
                "assists": player.assists,
                "net_worth": player.net_worth,
                "lane_role": player.lane_role,
                "lane_efficiency_pct": player.lane_efficiency_pct,
                "teamfight_participation": player.teamfight_participation,
            }
        )

    return pd.DataFrame(rows)


def validate_player_match(df: pd.DataFrame) -> None:
    if len(df) != 10:
        raise ValueError(
            f"Expected 10 players, found {len(df)}"
        )

    if df["account_id"].isna().any():
        print("WARNING: Some players have no account_id")

    if df["hero_id"].isna().any():
        raise ValueError(
            "Some players have no hero_id"
        )

    unusual_lane_efficiency = df[
        (df["lane_efficiency_pct"] < 0)
        | (df["lane_efficiency_pct"] > 100)
    ]

    if not unusual_lane_efficiency.empty:
        print(
            "\nWARNING: unusual lane_efficiency_pct values found:"
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
            "build the player_match Silver dataset."
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

    match = gem.parse(
        replay_path
    )

    if match.match_id != match_id:
        raise ValueError(
            f"Replay match_id mismatch. "
            f"Expected {match_id}, "
            f"got {match.match_id}"
        )

    print(
        f"Match ID: {match.match_id}"
    )

    print(
        f"Players found: {len(match.players)}"
    )

    df = build_player_match_dataframe(
        match
    )

    validate_player_match(
        df
    )

    print("\n--- player_match ---")
    print(
        df.to_string(
            index=False
        )
    )

    output_path = save_player_match(
        df,
        match_id,
    )

    print("\nSilver dataset saved:")
    print(output_path)


if __name__ == "__main__":
    main()