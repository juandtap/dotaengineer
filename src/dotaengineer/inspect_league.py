import json

import requests


BASE_URL = "https://api.opendota.com/api"
LEAGUE_ID = 19719


def main() -> None:
    url = f"{BASE_URL}/leagues/{LEAGUE_ID}/matches"

    response = requests.get(
        url,
        timeout=30,
    )

    response.raise_for_status()

    matches = response.json()

    print(f"Matches found: {len(matches)}")

    print("\nAvailable fields:")
    print(matches[0].keys())

    print("\nFirst match:")
    print(
        json.dumps(
            matches[0],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()