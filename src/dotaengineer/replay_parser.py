# from pathlib import Path

# import gem
# import pandas as pd

# REPLAY_PATH = Path("data/staging/replays/8943466067.dem")


# def main() -> None:
#     print(f"Parsing replay: {REPLAY_PATH}")

#     match = gem.parse(REPLAY_PATH)

#     print(f"\nReturned type: {type(match)}")
#     print("\nAvailable attributes:")
#     print(dir(match))

#     print(f"Players found: {len(match.players)}")

#     first_player = match.players[0]

#     print(f"\nFirst player type: {type(first_player)}")
#     print("\nFirst player attributes:")
#     print(dir(first_player))


# if __name__ == "__main__":
#     main()




# def main() -> None:
#     print(f"Parsing replay: {REPLAY_PATH}")

#     match = gem.parse(REPLAY_PATH)

#     print(f"\nMatch ID: {match.match_id}")
#     print(f"Players found: {len(match.players)}")

#     first_player = match.players[0]

#     print("\n--- First player sample ---")

#     fields = [
#         "player_name",
#         "player_id",
#         "account_id",
#         "team",
#         "is_radiant",
#         "hero_id",
#         "hero_name",
#         "kills",
#         "deaths",
#         "assists",
#         "gold_per_min",
#         "xp_per_min",
#         "net_worth",
#         "lane_role",
#         "lane_efficiency_pct",
#         "teamfight_participation",
#     ]

#     for field in fields:
#         value = getattr(first_player, field)

#         print(
#             f"{field}: "
#             f"{value!r} "
#             f"[{type(value).__name__}]"
#         )


# def build_player_match_dataframe(match) -> pd.DataFrame:
#     rows = []

#     for player in match.players:
#         rows.append(
#             {
#                 "match_id": match.match_id,
#                 "player_id": player.player_id,
#                 "account_id": player.account_id,
#                 "player_name": player.player_name,
#                 "team": player.team,
#                 "is_radiant": player.is_radiant,
#                 "hero_id": player.hero_id,
#                 "hero_name": player.hero_name,
#                 "kills": player.kills,
#                 "deaths": player.deaths,
#                 "assists": player.assists,
#                 "net_worth": player.net_worth,
#                 "lane_role": player.lane_role,
#                 "lane_efficiency_pct": player.lane_efficiency_pct,
#                 "teamfight_participation": player.teamfight_participation,
#             }
#         )

#     return pd.DataFrame(rows)


# def main() -> None:
#     print(f"Parsing replay: {REPLAY_PATH}")

#     match = gem.parse(REPLAY_PATH)

#     df = build_player_match_dataframe(match)

#     print("\n--- player_match ---")
#     print(df.to_string(index=False))

#     print("\n--- dtypes ---")
#     print(df.dtypes)


# if __name__ == "__main__":
#     main()

from pathlib import Path

import gem
import pandas as pd


REPLAY_PATH = Path("data/staging/replays/8943466067.dem")


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
        raise ValueError("Some players have no hero_id")

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
        Path("data/silver/player_match")
        / f"match_id={match_id}"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / "part-00000.parquet"

    df.to_parquet(
        output_path,
        index=False,
    )

    return output_path


def main() -> None:
    print(f"Parsing replay: {REPLAY_PATH}")

    match = gem.parse(REPLAY_PATH)

    df = build_player_match_dataframe(match)

    validate_player_match(df)

    print("\n--- player_match ---")
    print(df.to_string(index=False))

    print("\n--- dtypes ---")
    print(df.dtypes)

    output_path = save_player_match(
        df,
        match.match_id,
    )

    print("\nSilver dataset saved:")
    print(output_path)


if __name__ == "__main__":
    main()