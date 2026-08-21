import argparse
import math

import duckdb
import gem
import pandas as pd


PLAYER_TIMESERIES_PATH = (
    "data/silver/player_timeseries/*/*.parquet"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze player net worth growth "
            "around neutral camps."
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
        help="Player name",
    )

    return parser.parse_args()


def load_camp_zones() -> list[dict]:
    zones = gem.catalog.load_camp_zones()

    return zones["camps"]


def point_inside_ellipse(
    x: float,
    y: float,
    center_x: float,
    center_y: float,
    rx: float,
    ry: float,
) -> bool:
    if rx <= 0 or ry <= 0:
        return False

    normalized_distance = (
        ((x - center_x) / rx) ** 2
        + ((y - center_y) / ry) ** 2
    )

    return normalized_distance <= 1.0


def load_player_timeseries(
    con: duckdb.DuckDBPyConnection,
    match_id: int,
    player_name: str,
) -> pd.DataFrame:
    return con.execute(
        """
        WITH ordered AS (
            SELECT
                sample_index,
                game_time_seconds,
                x,
                y,
                net_worth,

                LAG(net_worth) OVER (
                    ORDER BY sample_index
                ) AS previous_net_worth

            FROM player_timeseries

            WHERE match_id = ?
              AND player_name = ?
              AND game_time_seconds >= 0
        )

        SELECT
            sample_index,
            game_time_seconds,
            x,
            y,
            net_worth,

            CASE
                WHEN previous_net_worth IS NULL
                THEN NULL
                ELSE net_worth - previous_net_worth
            END AS net_worth_delta

        FROM ordered

        ORDER BY sample_index
        """,
        [
            match_id,
            player_name,
        ],
    ).fetchdf()


def assign_camps(
    df: pd.DataFrame,
    camps: list[dict],
) -> pd.DataFrame:
    rows = []

    for row in df.itertuples(
        index=False
    ):
        matching_camps = []

        for camp in camps:
            center = camp["center"]
            zone = camp["zone"]

            inside = point_inside_ellipse(
                x=row.x,
                y=row.y,
                center_x=center["x"],
                center_y=center["y"],
                rx=zone["rx"],
                ry=zone["ry"],
            )

            if not inside:
                continue

            distance = math.sqrt(
                (row.x - center["x"]) ** 2
                + (row.y - center["y"]) ** 2
            )

            matching_camps.append(
                (
                    distance,
                    camp,
                )
            )

        # In case ellipses overlap, assign the snapshot
        # to the nearest camp center.
        if matching_camps:
            matching_camps.sort(
                key=lambda item: item[0]
            )

            _, selected_camp = (
                matching_camps[0]
            )

            camp_id = selected_camp["id"]
            camp_type = selected_camp["type"]

        else:
            camp_id = None
            camp_type = None

        rows.append(
            {
                "sample_index": row.sample_index,
                "game_time_seconds": (
                    row.game_time_seconds
                ),
                "x": row.x,
                "y": row.y,
                "net_worth": row.net_worth,
                "net_worth_delta": (
                    row.net_worth_delta
                ),
                "camp_id": camp_id,
                "camp_type": camp_type,
            }
        )

    return pd.DataFrame(rows)


def build_camp_summary(
    df: pd.DataFrame,
) -> pd.DataFrame:
    camp_samples = df[
        df["camp_id"].notna()
    ].copy()

    if camp_samples.empty:
        return pd.DataFrame()

    camp_samples["positive_nw_delta"] = (
        camp_samples[
            "net_worth_delta"
        ]
        .clip(lower=0)
        .fillna(0)
    )

    summary = (
        camp_samples
        .groupby(
            [
                "camp_id",
                "camp_type",
            ],
            as_index=False,
        )
        .agg(
            seconds_near_camp=(
                "sample_index",
                "count",
            ),
            positive_nw_growth=(
                "positive_nw_delta",
                "sum",
            ),
            max_positive_delta=(
                "positive_nw_delta",
                "max",
            ),
            first_second=(
                "game_time_seconds",
                "min",
            ),
            last_second=(
                "game_time_seconds",
                "max",
            ),
        )
    )

    summary[
        "nw_growth_per_second"
    ] = (
        summary["positive_nw_growth"]
        / summary["seconds_near_camp"]
    )

    summary = summary.sort_values(
        "positive_nw_growth",
        ascending=False,
    )

    return summary


def main() -> None:
    args = parse_arguments()

    camps = load_camp_zones()

    print(
        f"Neutral camps loaded: "
        f"{len(camps)}"
    )

    con = duckdb.connect()

    con.execute(
        f"""
        CREATE VIEW player_timeseries AS
        SELECT *
        FROM read_parquet(
            '{PLAYER_TIMESERIES_PATH}'
        )
        """
    )

    df = load_player_timeseries(
        con,
        args.match_id,
        args.player_name,
    )

    con.close()

    if df.empty:
        raise ValueError(
            f"No timeseries data found for "
            f"{args.player_name} in "
            f"match {args.match_id}."
        )

    assigned = assign_camps(
        df,
        camps,
    )

    summary = build_camp_summary(
        assigned
    )

    print("\n--- Player ---")
    print(
        f"Match: {args.match_id}"
    )
    print(
        f"Player: {args.player_name}"
    )
    print(
        f"Gameplay snapshots: "
        f"{len(df):,}"
    )

    snapshots_near_camp = (
        assigned["camp_id"]
        .notna()
        .sum()
    )

    print(
        f"Snapshots inside camp zones: "
        f"{snapshots_near_camp:,}"
    )

    if summary.empty:
        print(
            "\nNo snapshots were found "
            "inside neutral camp zones."
        )
        return

    print(
        "\n--- Neutral camp economy ---"
    )

    display = summary.copy()

    display[
        "positive_nw_growth"
    ] = (
        display[
            "positive_nw_growth"
        ]
        .round(0)
        .astype(int)
    )

    display[
        "nw_growth_per_second"
    ] = (
        display[
            "nw_growth_per_second"
        ]
        .round(2)
    )

    display[
        "first_minute"
    ] = (
        display["first_second"]
        / 60
    ).round(2)

    display[
        "last_minute"
    ] = (
        display["last_second"]
        / 60
    ).round(2)

    print(
        display[
            [
                "camp_id",
                "camp_type",
                "seconds_near_camp",
                "positive_nw_growth",
                "nw_growth_per_second",
                "max_positive_delta",
                "first_minute",
                "last_minute",
            ]
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    total_positive_growth = (
        df[
            "net_worth_delta"
        ]
        .clip(lower=0)
        .fillna(0)
        .sum()
    )

    camp_positive_growth = (
        summary[
            "positive_nw_growth"
        ].sum()
    )

    if total_positive_growth > 0:
        camp_share = (
            camp_positive_growth
            / total_positive_growth
            * 100
        )
    else:
        camp_share = 0

    print(
        "\n--- Camp contribution ---"
    )

    print(
        f"Total positive NW growth: "
        f"{total_positive_growth:,.0f}"
    )

    print(
        f"Positive NW growth while "
        f"inside camp zones: "
        f"{camp_positive_growth:,.0f}"
    )

    print(
        f"Share observed inside "
        f"camp zones: "
        f"{camp_share:.2f}%"
    )


if __name__ == "__main__":
    main()