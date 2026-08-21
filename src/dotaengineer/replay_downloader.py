import argparse
import bz2
import json
from pathlib import Path

import requests
import zstandard as zstd


BZIP2_MAGIC = b"BZh"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"

RAW_MATCHES_DIR = Path("data/raw/api/matches")
RAW_REPLAYS_DIR = Path("data/raw/replays")
STAGING_REPLAYS_DIR = Path("data/staging/replays")


def load_match(match_id: int) -> dict:
    match_path = (
        RAW_MATCHES_DIR
        / f"{match_id}.json"
    )

    if not match_path.exists():
        raise FileNotFoundError(
            f"Match JSON not found: {match_path}"
        )

    with match_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def download_replay(
    replay_url: str,
    match_id: int,
) -> Path:
    RAW_REPLAYS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        RAW_REPLAYS_DIR
        / f"{match_id}.dem.bz2"
    )

    temp_path = (
        RAW_REPLAYS_DIR
        / f"{match_id}.dem.bz2.part"
    )

    print("Downloading replay from:")
    print(replay_url)

    try:
        with requests.get(
            replay_url,
            stream=True,
            timeout=120,
            allow_redirects=True,
        ) as response:

            print(
                f"HTTP status: "
                f"{response.status_code}"
            )

            print(
                f"Content-Type: "
                f"{response.headers.get('Content-Type')}"
            )

            print(
                f"Content-Length: "
                f"{response.headers.get('Content-Length')}"
            )

            print(
                f"Final URL: "
                f"{response.url}"
            )

            response.raise_for_status()

            with temp_path.open("wb") as file:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        file.write(chunk)

        if temp_path.stat().st_size == 0:
            raise ValueError(
                "Downloaded replay is empty."
            )

        temp_path.replace(
            output_path
        )

    except Exception:
        if temp_path.exists():
            temp_path.unlink()

        raise

    return output_path


def detect_compression(
    compressed_path: Path,
) -> str:
    with compressed_path.open("rb") as file:
        magic = file.read(4)

    if magic.startswith(
        BZIP2_MAGIC
    ):
        return "bzip2"

    if magic == ZSTD_MAGIC:
        return "zstd"

    raise ValueError(
        f"Unknown replay compression format. "
        f"Magic bytes: {magic.hex(' ')}"
    )


def decompress_bzip2(
    compressed_path: Path,
    output_path: Path,
) -> None:
    with bz2.open(
        compressed_path,
        "rb",
    ) as source:

        with output_path.open(
            "wb",
        ) as destination:

            while chunk := source.read(
                1024 * 1024
            ):
                destination.write(
                    chunk
                )


def decompress_zstd(
    compressed_path: Path,
    output_path: Path,
) -> None:
    decompressor = (
        zstd.ZstdDecompressor()
    )

    with compressed_path.open(
        "rb",
    ) as source:

        with output_path.open(
            "wb",
        ) as destination:

            decompressor.copy_stream(
                source,
                destination,
            )


def decompress_replay(
    compressed_path: Path,
) -> Path:
    STAGING_REPLAYS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        STAGING_REPLAYS_DIR
        / compressed_path.name.replace(
            ".bz2",
            "",
        )
    )

    temp_path = Path(
        f"{output_path}.part"
    )

    compression = detect_compression(
        compressed_path
    )

    print(
        f"Compression detected: "
        f"{compression.upper()}"
    )

    try:
        if compression == "bzip2":
            decompress_bzip2(
                compressed_path,
                temp_path,
            )

        elif compression == "zstd":
            decompress_zstd(
                compressed_path,
                temp_path,
            )

        if not temp_path.exists():
            raise FileNotFoundError(
                "Replay decompression finished "
                "but output file was not created."
            )

        if temp_path.stat().st_size == 0:
            raise ValueError(
                "Decompressed replay is empty."
            )

        temp_path.replace(
            output_path
        )

    except Exception:
        if temp_path.exists():
            temp_path.unlink()

        raise

    return output_path


def format_size(path: Path) -> str:
    size_mb = (
        path.stat().st_size
        / (1024 * 1024)
    )

    return f"{size_mb:.2f} MB"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download and decompress "
            "a Dota 2 replay."
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

    match_id = args.match_id

    print(
        f"Processing match: "
        f"{match_id}"
    )

    match = load_match(
        match_id
    )

    replay_url = match.get(
        "replay_url"
    )

    if not replay_url:
        raise ValueError(
            f"Match {match_id} does not "
            f"contain replay_url."
        )

    compressed_path = download_replay(
        replay_url,
        match_id,
    )

    print(
        f"Compressed replay downloaded: "
        f"{compressed_path} "
        f"({format_size(compressed_path)})"
    )

    replay_path = decompress_replay(
        compressed_path
    )

    print(
        f"Replay decompressed: "
        f"{replay_path} "
        f"({format_size(replay_path)})"
    )


if __name__ == "__main__":
    main()