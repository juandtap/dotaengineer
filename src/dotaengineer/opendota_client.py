import argparse
import json
from pathlib import Path

import requests


BASE_URL = "https://api.opendota.com/api"
RAW_MATCHES_DIR = Path("data/raw/api/matches")


def get_match(match_id: int) -> dict:
    url = f"{BASE_URL}/matches/{match_id}"

    print(f"Fetching match {match_id} from OpenDota...")

    response = requests.get(
        url,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def save_raw_match(
    match: dict,
    match_id: int,
) -> Path:
    RAW_MATCHES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = RAW_MATCHES_DIR / f"{match_id}.json"

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            match,
            file,
            indent=2,
        )

    return output_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a Dota 2 match from OpenDota."
    )

    parser.add_argument(
        "match_id",
        type=int,
        help="Dota 2 match ID",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    match = get_match(args.match_id)

    output_path = save_raw_match(
        match,
        args.match_id,
    )

    print(f"Match downloaded: {args.match_id}")
    print(f"RAW file saved at: {output_path}")


if __name__ == "__main__":
    main()