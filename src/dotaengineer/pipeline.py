import argparse
from pathlib import Path

import gem

from opendota_client import get_match, save_raw_match
from replay_downloader import (
    download_replay,
    decompress_replay,
    format_size,
)
from replay_parser import (
    build_player_match_dataframe,
    validate_player_match,
    save_player_match,
)


RAW_MATCHES_DIR = Path("data/raw/api/matches")
RAW_REPLAYS_DIR = Path("data/raw/replays")
STAGING_REPLAYS_DIR = Path("data/staging/replays")
SILVER_PLAYER_MATCH_DIR = Path("data/silver/player_match")


def ingest_match(match_id: int) -> None:
    print("=" * 60)
    print(f"DOTAENGINEER — Processing match {match_id}")
    print("=" * 60)

    # ---------------------------------------------------------
    # STEP 1 — OpenDota metadata
    # ---------------------------------------------------------

    match_json_path = (
        RAW_MATCHES_DIR
        / f"{match_id}.json"
    )

    if match_json_path.exists():
        print(
            f"\n[1/4] RAW match JSON already exists:"
            f"\n{match_json_path}"
        )

        import json

        with match_json_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            match_data = json.load(file)

    else:
        print(
            "\n[1/4] Fetching match metadata "
            "from OpenDota..."
        )

        match_data = get_match(
            match_id
        )

        match_json_path = save_raw_match(
            match_data,
            match_id,
        )

        print(
            f"RAW match JSON saved:"
            f"\n{match_json_path}"
        )

    # ---------------------------------------------------------
    # STEP 2 — Replay download
    # ---------------------------------------------------------

    replay_url = match_data.get(
        "replay_url"
    )

    if not replay_url:
        raise ValueError(
            f"Match {match_id} does not "
            "contain a replay_url."
        )

    compressed_replay_path = (
        RAW_REPLAYS_DIR
        / f"{match_id}.dem.bz2"
    )

    if compressed_replay_path.exists():
        print(
            f"\n[2/4] RAW replay already exists:"
            f"\n{compressed_replay_path}"
            f"\nSize: "
            f"{format_size(compressed_replay_path)}"
        )

    else:
        print(
            "\n[2/4] Downloading replay..."
        )

        compressed_replay_path = (
            download_replay(
                replay_url,
                match_id,
            )
        )

        print(
            f"RAW replay saved:"
            f"\n{compressed_replay_path}"
            f"\nSize: "
            f"{format_size(compressed_replay_path)}"
        )

    # ---------------------------------------------------------
    # STEP 3 — Replay decompression
    # ---------------------------------------------------------

    replay_path = (
        STAGING_REPLAYS_DIR
        / f"{match_id}.dem"
    )

    if replay_path.exists():
        print(
            f"\n[3/4] Decompressed replay "
            f"already exists:"
            f"\n{replay_path}"
            f"\nSize: "
            f"{format_size(replay_path)}"
        )

    else:
        print(
            "\n[3/4] Decompressing replay..."
        )

        replay_path = decompress_replay(
            compressed_replay_path
        )

        print(
            f"Replay decompressed:"
            f"\n{replay_path}"
            f"\nSize: "
            f"{format_size(replay_path)}"
        )

    # ---------------------------------------------------------
    # STEP 4 — Replay parsing + Silver
    # ---------------------------------------------------------

    silver_path = (
        SILVER_PLAYER_MATCH_DIR
        / f"match_id={match_id}"
        / "part-00000.parquet"
    )

    if silver_path.exists():
        print(
            f"\n[4/4] Silver player_match "
            f"already exists:"
            f"\n{silver_path}"
        )

    else:
        print(
            "\n[4/4] Parsing replay..."
        )

        parsed_match = gem.parse(
            replay_path
        )

        if parsed_match.match_id != match_id:
            raise ValueError(
                "Replay match_id mismatch. "
                f"Expected {match_id}, "
                f"got {parsed_match.match_id}"
            )

        print(
            f"Players found: "
            f"{len(parsed_match.players)}"
        )

        player_match_df = (
            build_player_match_dataframe(
                parsed_match
            )
        )

        validate_player_match(
            player_match_df
        )

        silver_path = save_player_match(
            player_match_df,
            match_id,
        )

        print(
            f"Silver dataset saved:"
            f"\n{silver_path}"
        )

    # ---------------------------------------------------------
    # DONE
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print(
        f"Match {match_id} processed successfully."
    )
    print("=" * 60)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the DOTAENGINEER ingestion "
            "pipeline for a Dota 2 match."
        )
    )

    parser.add_argument(
        "match_id",
        type=int,
        help="Dota 2 match ID",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    ingest_match(
        args.match_id
    )


if __name__ == "__main__":
    main()