from pathlib import Path
import json
import requests


BASE_URL = "https://api.opendota.com/api"


def get_match(match_id: int) -> dict:
    url = f"{BASE_URL}/matches/{match_id}"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    return response.json()


def save_raw_match(match: dict, match_id: int) -> Path:
    output_dir = Path("data/raw/api/matches")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{match_id}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(match, file, indent=2)

    return output_path


if __name__ == "__main__":
    match_id = 8943466067

    match = get_match(match_id)
    output_path = save_raw_match(match, match_id)

    print(f"Match downloaded: {match_id}")
    print(f"RAW file saved at: {output_path}")