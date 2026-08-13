from pathlib import Path
import bz2
import json

import requests
import zstandard as zstd


MATCH_ID = 8943466067

BZIP2_MAGIC = b"BZh"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"

RAW_MATCHES_DIR = Path("data/raw/api/matches")
RAW_REPLAYS_DIR = Path("data/raw/replays")
STAGING_REPLAYS_DIR = Path("data/staging/replays")


def load_match(match_id: int) -> dict:
    match_path = RAW_MATCHES_DIR / f"{match_id}.json"

    if not match_path.exists():
        raise FileNotFoundError(
            f"Match JSON not found: {match_path}"
        )

    with match_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def download_replay(replay_url: str, match_id: int) -> Path:
    RAW_REPLAYS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_REPLAYS_DIR / f"{match_id}.dem.bz2"

    print(f"Downloading replay from:")
    print(replay_url)

    with requests.get(
        replay_url,
        stream=True,
        timeout=120,
        allow_redirects=True,
    ) as response:

        print(f"HTTP status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Content-Length: {response.headers.get('Content-Length')}")
        print(f"Final URL: {response.url}")

        response.raise_for_status()

        with output_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)

    if output_path.stat().st_size == 0:
        raise ValueError("Downloaded replay is empty.")

    return output_path


def detect_compression(compressed_path: Path) -> str:
    with compressed_path.open("rb") as file:
        magic = file.read(4)

    if magic.startswith(BZIP2_MAGIC):
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

    with bz2.open(compressed_path, "rb") as source:
        with output_path.open("wb") as destination:
            while chunk := source.read(1024 * 1024):
                destination.write(chunk)


def decompress_zstd(
    compressed_path: Path,
    output_path: Path,
) -> None:

    decompressor = zstd.ZstdDecompressor()

    with compressed_path.open("rb") as source:
        with output_path.open("wb") as destination:
            decompressor.copy_stream(source, destination)


def decompress_replay(compressed_path: Path) -> Path:
    STAGING_REPLAYS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = STAGING_REPLAYS_DIR / (
        compressed_path.name.replace(".bz2", "")
    )

    compression = detect_compression(compressed_path)

    print(f"Compression detected: {compression.upper()}")

    if compression == "bzip2":
        decompress_bzip2(
            compressed_path,
            output_path,
        )

    elif compression == "zstd":
        decompress_zstd(
            compressed_path,
            output_path,
        )

    if not output_path.exists():
        raise FileNotFoundError(
            "Replay decompression finished but output file was not created."
        )

    if output_path.stat().st_size == 0:
        raise ValueError(
            "Decompressed replay is empty."
        )

    return output_path


def format_size(path: Path) -> str:
    size_mb = path.stat().st_size / (1024 * 1024)
    return f"{size_mb:.2f} MB"


def main() -> None:
    print(f"Processing match: {MATCH_ID}")

    match = load_match(MATCH_ID)

    replay_url = match.get("replay_url")

    if not replay_url:
        raise ValueError(
            f"Match {MATCH_ID} does not contain replay_url."
        )

    compressed_path = download_replay(
        replay_url,
        MATCH_ID,
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