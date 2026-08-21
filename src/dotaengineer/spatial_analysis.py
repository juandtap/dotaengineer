import argparse

import duckdb
import gem


PLAYER_TIMESERIES_PATH = (
    "data/silver/player_timeseries/*/*.parquet"
)

GRID_SIZE = 10


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze spatial net worth growth "
            "from DOTAENGINEER Silver datasets."
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


def load_map_bounds() -> dict:
    constants = gem.catalog.load_map_constants()

    bounds = constants["world_bounds"]

    return {
        "xmin": float(bounds["xmin"]),
        "xmax": float(bounds["xmax"]),
        "ymin": float(bounds["ymin"]),
        "ymax": float(bounds["ymax"]),
    }


def main() -> None:
    args = parse_arguments()

    bounds = load_map_bounds()

    xmin = bounds["xmin"]
    xmax = bounds["xmax"]
    ymin = bounds["ymin"]
    ymax = bounds["ymax"]

    print("\n--- Map calibration ---")
    print(f"xmin: {xmin}")
    print(f"xmax: {xmax}")
    print(f"ymin: {ymin}")
    print(f"ymax: {ymax}")
    print(f"normalized grid: {GRID_SIZE} x {GRID_SIZE}")

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

    # ---------------------------------------------------------
    # Player information
    # ---------------------------------------------------------

    player_info = con.execute(
        """
        SELECT
            match_id,
            player_id,
            account_id,
            player_name,
            hero_name,
            is_radiant,
            MIN(game_time_seconds) AS first_second,
            MAX(game_time_seconds) AS last_second,
            COUNT(*) AS samples
        FROM player_timeseries
        WHERE match_id = ?
          AND player_name = ?
        GROUP BY
            match_id,
            player_id,
            account_id,
            player_name,
            hero_name,
            is_radiant
        """,
        [
            args.match_id,
            args.player_name,
        ],
    ).fetchdf()

    if player_info.empty:
        raise ValueError(
            f"Player '{args.player_name}' "
            f"not found in match {args.match_id}."
        )

    print("\n--- Player ---")
    print(player_info.to_string(index=False))

    # ---------------------------------------------------------
    # World coordinate range
    # ---------------------------------------------------------

    coordinate_range = con.execute(
        """
        SELECT
            ROUND(MIN(x), 2) AS min_x,
            ROUND(MAX(x), 2) AS max_x,
            ROUND(MIN(y), 2) AS min_y,
            ROUND(MAX(y), 2) AS max_y
        FROM player_timeseries
        WHERE match_id = ?
          AND player_name = ?
          AND game_time_seconds >= 0
        """,
        [
            args.match_id,
            args.player_name,
        ],
    ).fetchdf()

    print("\n--- Player world coordinate range ---")
    print(coordinate_range.to_string(index=False))

    # ---------------------------------------------------------
    # Normalized coordinate validation
    # ---------------------------------------------------------

    normalized_range = con.execute(
        f"""
        SELECT
            ROUND(
                MIN((x - {xmin}) / ({xmax} - {xmin})),
                4
            ) AS min_normalized_x,

            ROUND(
                MAX((x - {xmin}) / ({xmax} - {xmin})),
                4
            ) AS max_normalized_x,

            ROUND(
                MIN((y - {ymin}) / ({ymax} - {ymin})),
                4
            ) AS min_normalized_y,

            ROUND(
                MAX((y - {ymin}) / ({ymax} - {ymin})),
                4
            ) AS max_normalized_y

        FROM player_timeseries

        WHERE match_id = ?
          AND player_name = ?
          AND game_time_seconds >= 0
        """,
        [
            args.match_id,
            args.player_name,
        ],
    ).fetchdf()

    print("\n--- Player normalized coordinate range ---")
    print(normalized_range.to_string(index=False))

    # ---------------------------------------------------------
    # Delta statistics
    # ---------------------------------------------------------

    delta_stats = con.execute(
        """
        WITH ordered AS (
            SELECT
                sample_index,
                net_worth,

                LAG(net_worth) OVER (
                    ORDER BY sample_index
                ) AS previous_net_worth

            FROM player_timeseries

            WHERE match_id = ?
              AND player_name = ?
              AND game_time_seconds >= 0
        ),

        deltas AS (
            SELECT
                net_worth - previous_net_worth
                    AS net_worth_delta
            FROM ordered
            WHERE previous_net_worth IS NOT NULL
        )

        SELECT
            COUNT(*) AS snapshots,

            SUM(
                CASE
                    WHEN net_worth_delta > 0 THEN 1
                    ELSE 0
                END
            ) AS positive_snapshots,

            SUM(
                CASE
                    WHEN net_worth_delta = 0 THEN 1
                    ELSE 0
                END
            ) AS zero_snapshots,

            SUM(
                CASE
                    WHEN net_worth_delta < 0 THEN 1
                    ELSE 0
                END
            ) AS negative_snapshots,

            SUM(
                CASE
                    WHEN net_worth_delta > 0
                    THEN net_worth_delta
                    ELSE 0
                END
            ) AS total_positive_growth

        FROM deltas
        """,
        [
            args.match_id,
            args.player_name,
        ],
    ).fetchdf()

    print("\n--- Delta statistics ---")
    print(delta_stats.to_string(index=False))

    # ---------------------------------------------------------
    # Normalized spatial aggregation
    # ---------------------------------------------------------

    spatial_growth = con.execute(
        f"""
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
        ),

        normalized AS (
            SELECT
                game_time_seconds,
                x,
                y,

                (x - {xmin})
                / ({xmax} - {xmin})
                    AS normalized_x,

                (y - {ymin})
                / ({ymax} - {ymin})
                    AS normalized_y,

                net_worth - previous_net_worth
                    AS net_worth_delta

            FROM ordered

            WHERE previous_net_worth IS NOT NULL
        ),

        valid_growth AS (
            SELECT
                *,

                LEAST(
                    {GRID_SIZE - 1},
                    GREATEST(
                        0,
                        FLOOR(
                            normalized_x * {GRID_SIZE}
                        )::INTEGER
                    )
                ) AS grid_x,

                LEAST(
                    {GRID_SIZE - 1},
                    GREATEST(
                        0,
                        FLOOR(
                            normalized_y * {GRID_SIZE}
                        )::INTEGER
                    )
                ) AS grid_y

            FROM normalized

            WHERE net_worth_delta > 0
              AND normalized_x BETWEEN 0 AND 1
              AND normalized_y BETWEEN 0 AND 1
        ),

        totals AS (
            SELECT
                SUM(net_worth_delta)
                    AS all_positive_growth
            FROM valid_growth
        )

        SELECT
            grid_x,
            grid_y,

            COUNT(*) AS growth_events,

            SUM(net_worth_delta)
                AS total_nw_growth,

            ROUND(
                100.0
                * SUM(net_worth_delta)
                / MAX(all_positive_growth),
                2
            ) AS growth_share_pct,

            ROUND(
                AVG(net_worth_delta),
                2
            ) AS avg_nw_growth,

            MAX(net_worth_delta)
                AS max_nw_growth,

            ROUND(
                AVG(normalized_x),
                4
            ) AS avg_normalized_x,

            ROUND(
                AVG(normalized_y),
                4
            ) AS avg_normalized_y

        FROM valid_growth

        CROSS JOIN totals

        GROUP BY
            grid_x,
            grid_y

        ORDER BY
            total_nw_growth DESC
        """,
        [
            args.match_id,
            args.player_name,
        ],
    ).fetchdf()

    print(
        f"\n--- Spatial NW growth "
        f"({GRID_SIZE}x{GRID_SIZE} normalized grid) ---"
    )

    print(
        spatial_growth.head(20).to_string(
            index=False
        )
    )

    # ---------------------------------------------------------
    # Top cells summary
    # ---------------------------------------------------------

    top_cells = spatial_growth.head(5).copy()

    if not top_cells.empty:
        top_share = top_cells[
            "growth_share_pct"
        ].sum()

        print("\n--- Spatial concentration ---")

        print(
            f"Top 5 cells contain "
            f"{top_share:.2f}% "
            f"of observed positive NW growth."
        )

    con.close()


if __name__ == "__main__":
    main()