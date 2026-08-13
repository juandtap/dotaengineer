# DOTAENGINEER

DOTAENGINEER is a personal data engineering and analytics project built around professional Dota 2 matches.

The idea is pretty simple: collect match data, process Dota 2 replays, and look for interesting patterns that are not always obvious from regular match statistics.

The project started as a way to practice Data Engineering with real and constantly changing data, especially around professional tournaments like **The International**.

Eventually, I want to use the collected data for deeper analytics, visualizations, and maybe some Machine Learning experiments.

## Current Goal

For now, the goal is much smaller:

> Given a professional Dota 2 `match_id`, automatically collect the match data and download its replay.

The first test match used in the project is *LDG vs Team Resilience* (TI 2026 Group stage):

```text
8943466067
```

## Current Flow

```text
Match ID
   ↓
OpenDota API
   ↓
Raw match JSON
   ↓
Replay URL
   ↓
Valve Replay Server
   ↓
Compressed replay
   ↓
Decompressed .dem
```

The OpenDota response already contains a lot of useful information, including:

* players
* picks and bans
* objectives
* teamfights
* ability usage
* gold advantage
* XP advantage
* replay metadata

The `.dem` replay will be used later when more detailed game information is needed.

## Project Structure

```text
dotaengineer/
├── data/
│   ├── raw/
│   │   ├── api/
│   │   └── replays/
│   ├── staging/
│   └── silver/
├── notebooks/
├── src/
│   └── dotaengineer/
├── tests/
├── README.md
└── requirements.txt
```

### Raw

Original data downloaded from external sources.

This includes OpenDota JSON responses and compressed Valve replay files.

Raw files should not be modified after ingestion.

### Staging

Temporary files used during processing.

For example, decompressed `.dem` replay files live here and can be recreated from the compressed replay if needed.

### Silver

Clean and structured datasets will eventually be stored here, probably using Parquet.

This part is not implemented yet.

## Environment

The project is currently being developed using:

* Fedora on WSL2
* Python
* VSCODE with WSL integration
* OpenDota API
* Zstandard

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

On Fedora, install Zstandard:

```bash
sudo dnf install zstd
```

## A Small Replay Gotcha

One interesting thing showed up while testing replay downloads.

OpenDota returned a replay URL ending in:

```text
.dem.bz2
```

At first I assumed the file was compressed using BZip2.

Trying to decompress it with:

```bash
bzip2 -tvv replay.dem.bz2
```

returned:

```text
bad magic number (file not created by bzip2)
```

Checking the actual file instead:

```bash
file replay.dem.bz2
```

showed:

```text
Zstandard compressed data (v0.8+)
```

The first bytes were:

```text
28 b5 2f fd
```

which is the Zstandard magic number.

So even though the replay URL uses the `.bz2` extension, **the actual compression format for this replay is Zstandard**.

It can be decompressed with:

```bash
zstd -d replay.dem.bz2 -o replay.dem
```

Because of this, the downloader should eventually detect the compression format from the file contents instead of trusting the filename extension.

## Data Storage

Large data files are intentionally not tracked by Git.

This includes:

```text
data/raw/
data/staging/
data/silver/
```

Compressed replay files are kept as the original Raw source.

Decompressed `.dem` files are considered temporary because they can always be recreated from the compressed replay.

## Status

Currently working:

* [x] Fetch a match from OpenDota using a `match_id`
* [x] Store the original OpenDota JSON
* [x] Get the Valve replay URL from the match data
* [x] Download the compressed replay
* [x] Identify the actual replay compression format
* [x] Decompress a Zstandard replay into `.dem`

Next:

* [ ] Parse the `.dem` replay
* [ ] Explore available replay events
* [ ] Decide which data is worth storing
* [ ] Create structured Parquet datasets
* [ ] Build analytics on top of professional matches

## Long-Term Idea

The long-term goal is not to build another Dotabuff.

I want DOTAENGINEER to focus more on questions like:

> What interesting things can we find in professional Dota matches that normal match statistics don't immediately show?

That could include draft patterns, teamfight behavior, map movement, objective control, player tendencies, unusual strategies, and eventually ML-based experiments.

For now, though, the next challenge is simple:

**let's see what is actually inside a Dota 2 replay.**
