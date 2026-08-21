import argparse

import duckdb


PLAYER_TIMESERIES_PATH = (
    "data/silver/player_timeseries/*/*.parquet"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze player temporal data "
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


def main() -> None:
    args = parse_arguments()

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
            f"not found in match "
            f"{args.match_id}."
        )

    print("\n--- Player ---")

    print(
        player_info.to_string(
            index=False
        )
    )

    # ---------------------------------------------------------
    # Net worth by minute
    #
    # We select the last available snapshot in each minute.
    # Pre-game samples are intentionally excluded.
    # ---------------------------------------------------------

    net_worth_by_minute = con.execute(
        """
        WITH game_samples AS (
            SELECT
                match_id,
                player_id,
                player_name,
                hero_name,
                game_time_seconds,
                FLOOR(
                    game_time_seconds / 60
                )::INTEGER AS minute,
                x,
                y,
                net_worth,
                xp
            FROM player_timeseries
            WHERE match_id = ?
              AND player_name = ?
              AND game_time_seconds >= 0
        ),

        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        match_id,
                        player_id,
                        minute
                    ORDER BY
                        game_time_seconds DESC
                ) AS rn
            FROM game_samples
        )

        SELECT
            minute,
            ROUND(
                game_time_seconds,
                2
            ) AS game_second,
            net_worth,
            xp,
            ROUND(x, 2) AS x,
            ROUND(y, 2) AS y
        FROM ranked
        WHERE rn = 1
        ORDER BY minute
        """,
        [
            args.match_id,
            args.player_name,
        ],
    ).fetchdf()

    print(
        "\n--- Net worth by minute ---"
    )

    print(
        net_worth_by_minute.to_string(
            index=False
        )
    )

    # ---------------------------------------------------------
    # Net worth growth by minute
    # ---------------------------------------------------------

    net_worth_growth = con.execute(
        """
        WITH game_samples AS (
            SELECT
                match_id,
                player_id,
                game_time_seconds,
                FLOOR(
                    game_time_seconds / 60
                )::INTEGER AS minute,
                x,
                y,
                net_worth,
                xp
            FROM player_timeseries
            WHERE match_id = ?
              AND player_name = ?
              AND game_time_seconds >= 0
        ),

        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        match_id,
                        player_id,
                        minute
                    ORDER BY
                        game_time_seconds DESC
                ) AS rn
            FROM game_samples
        ),

        minute_snapshots AS (
            SELECT
                minute,
                game_time_seconds,
                x,
                y,
                net_worth,
                xp
            FROM ranked
            WHERE rn = 1
        ),

        growth AS (
            SELECT
                minute,
                game_time_seconds,
                x,
                y,
                net_worth,
                xp,

                net_worth
                - LAG(net_worth) OVER (
                    ORDER BY minute
                ) AS net_worth_gained,

                xp
                - LAG(xp) OVER (
                    ORDER BY minute
                ) AS xp_gained

            FROM minute_snapshots
        )

        SELECT
            minute,
            net_worth,
            net_worth_gained,
            xp,
            xp_gained,
            ROUND(x, 2) AS x,
            ROUND(y, 2) AS y
        FROM growth
        ORDER BY minute
        """,
        [
            args.match_id,
            args.player_name,
        ],
    ).fetchdf()

    print(
        "\n--- Growth by minute ---"
    )

    print(
        net_worth_growth.to_string(
            index=False
        )
    )

    # ---------------------------------------------------------
    # Best economy minutes
    # ---------------------------------------------------------

    best_minutes = con.execute(
        """
        WITH game_samples AS (
            SELECT
                match_id,
                player_id,
                game_time_seconds,
                FLOOR(
                    game_time_seconds / 60
                )::INTEGER AS minute,
                x,
                y,
                net_worth
            FROM player_timeseries
            WHERE match_id = ?
              AND player_name = ?
              AND game_time_seconds >= 0
        ),

        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        match_id,
                        player_id,
                        minute
                    ORDER BY
                        game_time_seconds DESC
                ) AS rn
            FROM game_samples
        ),

        minute_snapshots AS (
            SELECT
                minute,
                x,
                y,
                net_worth
            FROM ranked
            WHERE rn = 1
        ),

        growth AS (
            SELECT
                minute,
                x,
                y,
                net_worth,

                net_worth
                - LAG(net_worth) OVER (
                    ORDER BY minute
                ) AS net_worth_gained

            FROM minute_snapshots
        )

        SELECT
            minute,
            net_worth_gained,
            net_worth,
            ROUND(x, 2) AS x,
            ROUND(y, 2) AS y
        FROM growth
        WHERE net_worth_gained IS NOT NULL
        ORDER BY net_worth_gained DESC
        LIMIT 10
        """,
        [
            args.match_id,
            args.player_name,
        ],
    ).fetchdf()

    print(
        "\n--- Best economy minutes ---"
    )

    print(
        best_minutes.to_string(
            index=False
        )
    )

    con.close()


if __name__ == "__main__":
    main()