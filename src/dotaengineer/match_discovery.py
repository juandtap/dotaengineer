import argparse
from datetime import datetime, timezone
from pathlib import Path

import requests

from pipeline import ingest_match


BASE_URL = "https://api.opendota.com/api"
LEAGUE_ID = 19719

RAW_MATCHES_DIR = Path("data/raw/api/matches")


def get_league_matches(league_id: int) -> list[dict]:
    url = f"{BASE_URL}/leagues/{league_id}/matches"

    response = requests.get(
        url,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def get_ingested_match_ids() -> set[int]:
    if not RAW_MATCHES_DIR.exists():
        return set()

    match_ids = set()

    for path in RAW_MATCHES_DIR.glob("*.json"):
        try:
            match_ids.add(int(path.stem))
        except ValueError:
            continue

    return match_ids


def get_match_date(start_time: int | None) -> str | None:
    if not start_time:
        return None

    return datetime.fromtimestamp(
        start_time,
        tz=timezone.utc,
    ).strftime("%Y-%m-%d")


def format_match_time(start_time: int | None) -> str:
    if not start_time:
        return "Unknown"

    return datetime.fromtimestamp(
        start_time,
        tz=timezone.utc,
    ).strftime("%Y-%m-%d %H:%M UTC")


def get_team_display(match: dict, side: str) -> str:
    name = match.get(f"{side}_team_name")

    if name:
        return name

    team_id = match.get(f"{side}_team_id")

    if team_id:
        return f"Team {team_id}"

    return "Unknown"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Discover matches from "
            "The International 2026."
        )
    )

    parser.add_argument(
        "--date",
        type=str,
        help="Filter by UTC date, e.g. 2026-08-20",
    )

    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Ingest pending matches",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    league_matches = get_league_matches(
        LEAGUE_ID
    )

    ingested_match_ids = (
        get_ingested_match_ids()
    )

    selected_matches = []

    for match in league_matches:
        match_date = get_match_date(
            match.get("start_time")
        )

        if args.date and match_date != args.date:
            continue

        selected_matches.append(match)

    selected_matches.sort(
        key=lambda match: match.get(
            "start_time",
            0,
        )
    )

    print(f"League ID: {LEAGUE_ID}")
    print(
        f"Total league matches: "
        f"{len(league_matches)}"
    )
    print(
        f"Matches selected: "
        f"{len(selected_matches)}"
    )

    print()

    for match in selected_matches:
        match_id = match["match_id"]

        radiant = get_team_display(
            match,
            "radiant",
        )

        dire = get_team_display(
            match,
            "dire",
        )

        match_time = format_match_time(
            match.get("start_time")
        )

        status = (
            "INGESTED"
            if match_id in ingested_match_ids
            else "PENDING"
        )

        print(
            f"{match_id} | "
            f"{match_time} | "
            f"{radiant} vs {dire} | "
            f"{status}"
        )

    if not args.ingest:
        return

    pending_matches = [
        match
        for match in selected_matches
        if match["match_id"]
        not in ingested_match_ids
    ]

    print(
        f"\nMatches to ingest: "
        f"{len(pending_matches)}"
    )

    for index, match in enumerate(
        pending_matches,
        start=1,
    ):
        match_id = match["match_id"]

        print("\n" + "#" * 60)
        print(
            f"Batch match "
            f"{index}/{len(pending_matches)}"
        )
        print("#" * 60)

        ingest_match(match_id)


if __name__ == "__main__":
    main()