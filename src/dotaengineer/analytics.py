from pathlib import Path

import duckdb


MATCH_PATH = "data/silver/match/*/*.parquet"
PLAYER_MATCH_PATH = "data/silver/player_match/*/*.parquet"


def main() -> None:
    con = duckdb.connect()

    con.execute(
        f"""
        CREATE OR REPLACE VIEW matches AS
        SELECT *
        FROM read_parquet('{MATCH_PATH}')
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE VIEW player_matches AS
        SELECT *
        FROM read_parquet('{PLAYER_MATCH_PATH}')
        """
    )

    print("\n--- Dataset summary ---")

    summary = con.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM matches) AS matches,
            (SELECT COUNT(*) FROM player_matches) AS player_rows,
            (SELECT COUNT(DISTINCT player_name) FROM player_matches)
                AS unique_players
        """
    ).fetchdf()

    print(summary.to_string(index=False))

    print("\n--- Top kills ---")

    top_kills = con.execute(
        """
        SELECT
            player_name,
            COUNT(*) AS games,
            SUM(kills) AS kills,
            SUM(deaths) AS deaths,
            SUM(assists) AS assists,
            ROUND(AVG(kda), 2) AS avg_kda
        FROM player_matches
        GROUP BY player_name
        ORDER BY kills DESC
        LIMIT 10
        """
    ).fetchdf()

    print(top_kills.to_string(index=False))

    print("\n--- Highest net worth games ---")

    top_net_worth = con.execute(
        """
        SELECT
            match_id,
            player_name,
            hero_name,
            net_worth
        FROM player_matches
        ORDER BY net_worth DESC
        LIMIT 10
        """
    ).fetchdf()

    print(top_net_worth.to_string(index=False))


if __name__ == "__main__":
    main()