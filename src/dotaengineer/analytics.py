import duckdb


MATCH_PATH = "data/silver/match/*/*.parquet"
PLAYER_MATCH_PATH = "data/silver/player_match/*/*.parquet"


def main() -> None:
    con = duckdb.connect()

    # ---------------------------------------------------------
    # Views
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 1. Dataset summary
    # ---------------------------------------------------------

    print("\n--- Dataset summary ---")

    summary = con.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM matches) AS matches,
            (SELECT COUNT(*) FROM player_matches) AS player_rows,
            (
                SELECT COUNT(DISTINCT account_id)
                FROM player_matches
            ) AS unique_players
        """
    ).fetchdf()

    print(summary.to_string(index=False))

    # ---------------------------------------------------------
    # 2. Top kills
    # ---------------------------------------------------------

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
        GROUP BY
            account_id,
            player_name
        ORDER BY kills DESC
        LIMIT 10
        """
    ).fetchdf()

    print(top_kills.to_string(index=False))

    # ---------------------------------------------------------
    # 3. Highest net worth games
    # ---------------------------------------------------------

    print("\n--- Highest net worth games ---")

    highest_net_worth = con.execute(
        """
        SELECT
            pm.match_id,
            pm.player_name,
            REPLACE(
                pm.hero_name,
                'npc_dota_hero_',
                ''
            ) AS hero,
            ROUND(m.duration_minutes, 2) AS match_minutes,
            pm.net_worth
        FROM player_matches pm
        JOIN matches m
            ON pm.match_id = m.match_id
        ORDER BY pm.net_worth DESC
        LIMIT 10
        """
    ).fetchdf()

    print(highest_net_worth.to_string(index=False))

    # ---------------------------------------------------------
    # 4. Net worth per minute
    # ---------------------------------------------------------

    print("\n--- Highest net worth per minute ---")

    net_worth_per_minute = con.execute(
        """
        SELECT
            pm.match_id,
            pm.player_name,
            REPLACE(
                pm.hero_name,
                'npc_dota_hero_',
                ''
            ) AS hero,
            ROUND(m.duration_minutes, 2) AS match_minutes,
            pm.net_worth,
            ROUND(
                pm.net_worth
                / NULLIF(m.duration_minutes, 0),
                2
            ) AS net_worth_per_min
        FROM player_matches pm
        JOIN matches m
            ON pm.match_id = m.match_id
        ORDER BY net_worth_per_min DESC
        LIMIT 10
        """
    ).fetchdf()

    print(net_worth_per_minute.to_string(index=False))

    # ---------------------------------------------------------
    # 5. Hero damage per 1,000 net worth
    # ---------------------------------------------------------

    print(
        "\n--- Hero damage per 1,000 net worth ---"
    )

    damage_efficiency = con.execute(
        """
        SELECT
            pm.match_id,
            pm.player_name,
            REPLACE(
                pm.hero_name,
                'npc_dota_hero_',
                ''
            ) AS hero,
            pm.hero_damage,
            pm.net_worth,
            ROUND(
                pm.hero_damage
                / NULLIF(pm.net_worth, 0)
                * 1000,
                2
            ) AS hero_damage_per_1k_net_worth
        FROM player_matches pm
        WHERE pm.net_worth > 0
        ORDER BY hero_damage_per_1k_net_worth DESC
        LIMIT 10
        """
    ).fetchdf()

    print(damage_efficiency.to_string(index=False))

    # ---------------------------------------------------------
    # 6. Highest teamfight participation
    # ---------------------------------------------------------

    print(
        "\n--- Highest teamfight participation ---"
    )

    teamfight_participation = con.execute(
        """
        SELECT
            player_name,
            COUNT(*) AS games,
            ROUND(
                AVG(teamfight_participation) * 100,
                2
            ) AS avg_teamfight_participation_pct,
            ROUND(
                MIN(teamfight_participation) * 100,
                2
            ) AS lowest_game_pct,
            ROUND(
                MAX(teamfight_participation) * 100,
                2
            ) AS highest_game_pct
        FROM player_matches
        GROUP BY
            account_id,
            player_name
        ORDER BY avg_teamfight_participation_pct DESC
        LIMIT 10
        """
    ).fetchdf()

    print(teamfight_participation.to_string(index=False))

    # ---------------------------------------------------------
    # 7. Impact with low economy
    #
    # Experimental metric:
    # teamfight participation weighted by hero damage,
    # normalized by net worth.
    #
    # This is NOT an official Dota metric.
    # ---------------------------------------------------------

    print("\n--- Low economy impact score ---")

    low_economy_impact = con.execute(
        """
        SELECT
            pm.match_id,
            pm.player_name,
            REPLACE(
                pm.hero_name,
                'npc_dota_hero_',
                ''
            ) AS hero,
            pm.net_worth,
            pm.hero_damage,
            ROUND(
                pm.teamfight_participation * 100,
                2
            ) AS teamfight_participation_pct,

            ROUND(
                (
                    pm.hero_damage
                    * pm.teamfight_participation
                )
                / NULLIF(pm.net_worth, 0)
                * 1000,
                2
            ) AS impact_score

        FROM player_matches pm

        WHERE
            pm.net_worth > 0
            AND pm.teamfight_participation IS NOT NULL

        ORDER BY impact_score DESC

        LIMIT 10
        """
    ).fetchdf()

    print(low_economy_impact.to_string(index=False))

    con.close()


if __name__ == "__main__":
    main()