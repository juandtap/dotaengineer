import argparse
from pathlib import Path

import duckdb
import gem
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


PLAYER_TIMESERIES_PATH = (
    "data/silver/player_timeseries/*/*.parquet"
)

OUTPUT_DIR = Path("outputs/heatmaps")

GRID_SIZE = 10

MIN_SECONDS_FOR_EFFICIENCY = 60


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate movement, net worth growth, "
            "and economic efficiency maps."
        )
    )

    parser.add_argument(
        "match_id",
        type=int,
        help="Dota 2 match ID",
    )

    parser.add_argument(
        "player_name",
        type=str,
        help="Player name",
    )

    return parser.parse_args()


def load_map_constants() -> dict:
    return gem.catalog.load_map_constants()


def get_map_path() -> Path:
    map_path = (
        Path.home()
        / ".cache"
        / "gem-dota"
        / "reports"
        / "maps"
        / "Game_map_7.40.jpg"
    )

    if not map_path.exists():
        raise FileNotFoundError(
            f"Map image not found: {map_path}"
        )

    return map_path


def load_player_data(
    con: duckdb.DuckDBPyConnection,
    match_id: int,
    player_name: str,
):
    return con.execute(
        """
        WITH ordered AS (
            SELECT
                sample_index,
                game_time_seconds,
                x,
                y,
                net_worth,

                LAG(net_worth) OVER (
                    ORDER BY sample_index
                ) AS previous_net_worth

            FROM player_timeseries

            WHERE match_id = ?
              AND player_name = ?
              AND game_time_seconds >= 0
        )

        SELECT
            sample_index,
            game_time_seconds,
            x,
            y,
            net_worth,

            CASE
                WHEN previous_net_worth IS NULL
                THEN NULL
                ELSE net_worth - previous_net_worth
            END AS net_worth_delta

        FROM ordered

        ORDER BY sample_index
        """,
        [
            match_id,
            player_name,
        ],
    ).fetchdf()


def normalize_coordinates(
    df,
    bounds: dict,
):
    xmin = float(bounds["xmin"])
    xmax = float(bounds["xmax"])
    ymin = float(bounds["ymin"])
    ymax = float(bounds["ymax"])

    df = df.copy()

    df["normalized_x"] = (
        (df["x"] - xmin)
        / (xmax - xmin)
    )

    df["normalized_y"] = (
        (df["y"] - ymin)
        / (ymax - ymin)
    )

    return df[
        df["normalized_x"].between(0, 1)
        & df["normalized_y"].between(0, 1)
    ]


def build_grid(
    x_values,
    y_values,
    weights=None,
):
    grid, _, _ = np.histogram2d(
        x_values,
        y_values,
        bins=GRID_SIZE,
        range=[
            [0, 1],
            [0, 1],
        ],
        weights=weights,
    )

    return grid.T


def safe_divide(
    numerator: np.ndarray,
    denominator: np.ndarray,
) -> np.ndarray:
    result = np.zeros_like(
        numerator,
        dtype=float,
    )

    np.divide(
        numerator,
        denominator,
        out=result,
        where=denominator > 0,
    )

    return result


def save_heatmap(
    map_image,
    heatmap: np.ndarray,
    title: str,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(
        figsize=(10, 10)
    )

    ax.imshow(
        map_image,
        extent=[
            0,
            1,
            0,
            1,
        ],
        origin="upper",
    )

    masked = np.ma.masked_where(
        heatmap <= 0,
        heatmap,
    )

    ax.imshow(
        masked,
        extent=[
            0,
            1,
            0,
            1,
        ],
        origin="lower",
        alpha=0.6,
        interpolation="bilinear",
    )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.set_title(title)

    ax.set_xlabel(
        "Normalized map X"
    )

    ax.set_ylabel(
        "Normalized map Y"
    )

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close()


def main() -> None:
    args = parse_arguments()

    constants = load_map_constants()
    bounds = constants["world_bounds"]

    map_path = get_map_path()

    con = duckdb.connect()

    con.execute(
        f"""
        CREATE VIEW player_timeseries AS
        SELECT *
        FROM read_parquet(
            '{PLAYER_TIMESERIES_PATH}'
        )
        """
    )

    df = load_player_data(
        con,
        args.match_id,
        args.player_name,
    )

    con.close()

    if df.empty:
        raise ValueError(
            f"No timeseries data found for "
            f"{args.player_name} in "
            f"{args.match_id}."
        )

    df = normalize_coordinates(
        df,
        bounds,
    )

    # ---------------------------------------------------------
    # Movement Density
    #
    # One sample ~= one second.
    # Therefore this is approximately seconds spent per cell.
    # ---------------------------------------------------------

    movement_grid = build_grid(
        df["normalized_x"].to_numpy(),
        df["normalized_y"].to_numpy(),
    )

    # ---------------------------------------------------------
    # Positive Net Worth Growth
    # ---------------------------------------------------------

    positive_growth = df[
        df["net_worth_delta"] > 0
    ].copy()

    nw_growth_grid = build_grid(
        positive_growth[
            "normalized_x"
        ].to_numpy(),
        positive_growth[
            "normalized_y"
        ].to_numpy(),
        positive_growth[
            "net_worth_delta"
        ].to_numpy(),
    )

    # ---------------------------------------------------------
    # Economic Spatial Efficiency
    #
    # Positive NW growth / time spent in cell.
    #
    # Only cells with at least
    # MIN_SECONDS_FOR_EFFICIENCY are considered.
    #
    # This is an experimental metric.
    # ---------------------------------------------------------

    efficiency_grid = safe_divide(
        nw_growth_grid,
        movement_grid,
    )

    efficiency_grid[
        movement_grid < MIN_SECONDS_FOR_EFFICIENCY
    ] = 0

    # ---------------------------------------------------------
    # Console summary
    # ---------------------------------------------------------

    print("\n--- Spatial summary ---")

    print(
        f"Player: {args.player_name}"
    )

    print(
        f"Match: {args.match_id}"
    )

    print(
        f"Gameplay samples: "
        f"{len(df):,}"
    )

    print(
        f"Positive NW events: "
        f"{len(positive_growth):,}"
    )

    print(
        f"Positive NW growth: "
        f"{positive_growth['net_worth_delta'].sum():,.0f}"
    )

    print(
        f"Movement grid total samples: "
        f"{movement_grid.sum():,.0f}"
    )

    print(
        f"NW grid total growth: "
        f"{nw_growth_grid.sum():,.0f}"
    )

    print(
        f"Minimum exposure for efficiency: "
        f"{MIN_SECONDS_FOR_EFFICIENCY} seconds"
    )

    # ---------------------------------------------------------
    # Highest economic efficiency cells
    # ---------------------------------------------------------

    rows = []

    for grid_y in range(GRID_SIZE):
        for grid_x in range(GRID_SIZE):
            seconds = movement_grid[
                grid_y,
                grid_x,
            ]

            if seconds < MIN_SECONDS_FOR_EFFICIENCY:
                continue

            growth = nw_growth_grid[
                grid_y,
                grid_x,
            ]

            efficiency = efficiency_grid[
                grid_y,
                grid_x,
            ]

            rows.append(
                (
                    grid_x,
                    grid_y,
                    seconds,
                    growth,
                    efficiency,
                )
            )

    rows.sort(
        key=lambda row: row[4],
        reverse=True,
    )

    print(
        "\n--- Highest economic efficiency cells "
        f"(minimum {MIN_SECONDS_FOR_EFFICIENCY}s exposure) ---"
    )

    print(
        "grid_x grid_y seconds "
        "nw_growth nw_per_second"
    )

    for row in rows[:15]:
        grid_x = row[0]
        grid_y = row[1]
        seconds = row[2]
        growth = row[3]
        efficiency = row[4]

        print(
            f"{grid_x:6d} "
            f"{grid_y:6d} "
            f"{seconds:7.0f} "
            f"{growth:9.0f} "
            f"{efficiency:13.2f}"
        )

    # ---------------------------------------------------------
    # Map images
    # ---------------------------------------------------------

    map_image = Image.open(
        map_path
    ).convert("RGB")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_player_name = (
        args.player_name
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )

    movement_path = (
        OUTPUT_DIR
        / (
            f"{args.match_id}_"
            f"{safe_player_name}_"
            f"movement_density.png"
        )
    )

    nw_growth_path = (
        OUTPUT_DIR
        / (
            f"{args.match_id}_"
            f"{safe_player_name}_"
            f"networth_growth.png"
        )
    )

    efficiency_path = (
        OUTPUT_DIR
        / (
            f"{args.match_id}_"
            f"{safe_player_name}_"
            f"economic_efficiency.png"
        )
    )

    save_heatmap(
        map_image,
        movement_grid,
        (
            f"{args.player_name} — Movement Density\n"
            f"Match {args.match_id}"
        ),
        movement_path,
    )

    save_heatmap(
        map_image,
        nw_growth_grid,
        (
            f"{args.player_name} — Net Worth Growth\n"
            f"Match {args.match_id}"
        ),
        nw_growth_path,
    )

    save_heatmap(
        map_image,
        efficiency_grid,
        (
            f"{args.player_name} — Economic Spatial Efficiency\n"
            f"Match {args.match_id}\n"
            f"Minimum exposure: "
            f"{MIN_SECONDS_FOR_EFFICIENCY}s"
        ),
        efficiency_path,
    )

    print("\nHeatmaps saved:")

    print(
        f"Movement:"
        f"\n{movement_path}"
    )

    print(
        f"\nNet worth growth:"
        f"\n{nw_growth_path}"
    )

    print(
        f"\nEconomic efficiency:"
        f"\n{efficiency_path}"
    )


if __name__ == "__main__":
    main()