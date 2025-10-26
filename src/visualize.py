from pathlib import Path
import re

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from data_connection import load_table

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output" / "visualizations"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def sanitize(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", s).strip("_")


def _mean_or_nan(lst):
    if not isinstance(lst, (list, tuple, np.ndarray)) or len(lst) == 0:
        return np.nan
    try:
        return float(np.mean([float(x) for x in lst]))
    except Exception:
        return np.nan


def _prepare_perf():
    perf_df = load_table("performance")
    if perf_df is None or perf_df.empty:
        return None

    # compute per-row mean reps and mean weight
    perf_df = perf_df.copy()
    perf_df["mean_reps"] = perf_df["reps"].apply(_mean_or_nan)
    perf_df["mean_weight"] = perf_df["weights"].apply(_mean_or_nan)
    perf_df["date"] = pd.to_datetime(perf_df["date"])
    return perf_df


def main():
    perf_df = _prepare_perf()
    if perf_df is None:
        print("No performance data found.")
        return

    ex_df = load_table("exercises")
    wk_df = load_table("workouts")

    # map exercise metadata
    ex_map = {}
    if not ex_df.empty:
        for r in ex_df.to_dict(orient="records"):
            try:
                ex_map[int(r["id"])] = r
            except Exception:
                continue

    # group performance by workout and exercise
    # assume performance rows may reference workout_id
    if "workout_id" not in perf_df.columns:
        raise RuntimeError("performance table missing workout_id column")

    # For each workout, make a figure with one subplot per exercise
    for w in (wk_df.to_dict(orient="records") if not wk_df.empty else []):
        wid = int(w.get("id"))
        wk_name = w.get("name") or f"workout_{wid}"
        perf_w = perf_df[perf_df["workout_id"].astype(int) == wid]
        if perf_w.empty:
            continue

        # exercises present in this workout (from workout table) or perf data
        ex_ids = w.get("exercises")
        ex_ids = [int(x) for x in ex_ids]
        if not ex_ids:
            ex_ids = sorted(perf_w["exercise_id"].unique())

        n = len(ex_ids)
        cols = 2
        rows = (n + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(8 * cols, 3 * rows), squeeze=False)

        sns.set_style("whitegrid")

        for idx, ex_id in enumerate(ex_ids):
            r = idx // cols
            c = idx % cols
            ax = axes[r][c]
            perf_ex = perf_w[perf_w["exercise_id"].astype(int) == int(ex_id)]
            if perf_ex.empty:
                ax.text(0.5, 0.5, "no data", ha="center", va="center")
                ax.set_title(f"exercise {ex_id}")
                continue

            # aggregate by date
            agg = (
                perf_ex.groupby("date", as_index=False)
                .agg(avg_reps=("mean_reps", "mean"), avg_weight=("mean_weight", "mean"))
                .sort_values("date")
            )

            # plot reps and weight with seaborn lineplot
            sns.lineplot(data=agg, x="date", y="avg_reps", marker="o", ax=ax, label="avg reps")
            ax2 = ax.twinx()
            sns.lineplot(data=agg, x="date", y="avg_weight", marker="s", ax=ax2, color="orange", label="avg weight")

            meta = ex_map.get(int(ex_id), {})
            title = meta.get("name", f"exercise_{ex_id}")
            meta_parts = []
            if meta.get("sets") is not None:
                meta_parts.append(f"sets={meta.get('sets')}")
            if meta.get("reps") is not None:
                # reps may be list/array
                try:
                    reps = meta.get("reps")
                    if hasattr(reps, "astype"):
                        reps = "-".join(map(str, reps))
                        reps = reps.replace("-99", "+")
                    meta_parts.append(f"reps={reps}")
                except Exception:
                    meta_parts.append(f"reps={meta.get('reps')}")
            if meta.get("rest") is not None:
                meta_parts.append(f"rest={meta.get('rest')}s")

            ax.set_title(f"{title} ({', '.join(meta_parts)})")
            ax.set_xlabel("")
            ax.set_ylabel("avg reps")
            ax2.set_ylabel("avg weight (kg)")
            try:
                from matplotlib.ticker import MaxNLocator
                from matplotlib.dates import DateFormatter, AutoDateLocator

                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
                ax2.yaxis.set_major_locator(MaxNLocator(integer=True))
                ax.xaxis.set_major_locator(AutoDateLocator())
                ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
                for lbl in ax.get_xticklabels():
                    lbl.set_rotation(30)
                    lbl.set_ha("right")
            except Exception:
                pass

            # small subtitle with meta
            # ax.text(0.01, -0.25, " | ".join(meta_parts), transform=ax.transAxes, fontsize=8)

        # hide empty subplots
        for i in range(n, rows * cols):
            r = i // cols
            c = i % cols
            axes[r][c].axis("off")

        fig.suptitle(f"{wk_name} (id={wid})")
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        out_fname = OUT_DIR / f"workout_{wid}_{sanitize(wk_name)}.png"
        fig.savefig(out_fname, dpi=150)
        plt.close(fig)
        print("written", out_fname)


if __name__ == "__main__":
    main()

# filepath: /Users/erbs/code/fitnessplan/src/visualize.py
from pathlib import Path
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from data_connection import load_table

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output" / "visualizations"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def sanitize(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", s).strip("_")


def _mean_or_nan(lst):
    if not isinstance(lst, (list, tuple, np.ndarray)) or len(lst) == 0:
        return np.nan
    try:
        return float(np.mean([float(x) for x in lst]))
    except Exception:
        return np.nan


def main():
    perf_df = load_table("performance")
    if perf_df is None or perf_df.empty:
        print("No performance data found.")
        return

    # ensure expected columns exist
    for col in ("exercise_id", "date", "reps", "weights"):
        if col not in perf_df.columns:
            raise RuntimeError(f"performance missing column: {col}")

    # compute per-row mean reps and mean weight
    perf_df = perf_df.copy()
    perf_df["mean_reps"] = perf_df["reps"].apply(_mean_or_nan)
    perf_df["mean_weight"] = perf_df["weights"].apply(_mean_or_nan)

    # convert date to datetime for plotting and grouping
    perf_df["date"] = pd.to_datetime(perf_df["date"])

    # group by exercise and date, compute average of the per-row means
    grouped = (
        perf_df.groupby(["exercise_id", "date"], as_index=False)
        .agg(avg_reps=("mean_reps", "mean"), avg_weight=("mean_weight", "mean"))
    )

    # load exercise metadata for labels
    ex_df = load_table("exercises")
    ex_map = {}
    if ex_df is not None and not ex_df.empty:
        for r in ex_df.to_dict(orient="records"):
            try:
                ex_map[int(r["id"])] = r.get("name") or f"exercise_{r['id']}"
            except Exception:
                continue

    # create a plot per exercise
    exercise_ids = sorted(grouped["exercise_id"].unique())
    for ex_id in exercise_ids:
        sub = grouped[grouped["exercise_id"] == ex_id].sort_values("date")
        if sub.empty:
            continue

        fig, ax1 = plt.subplots(figsize=(8, 4))
        ax1.plot(sub["date"], sub["avg_reps"], marker="o", color="tab:blue", label="avg reps")
        ax1.set_xlabel("date")
        ax1.set_ylabel("avg reps", color="tab:blue")
        ax1.tick_params(axis="y", labelcolor="tab:blue")

        ax2 = ax1.twinx()
        ax2.plot(sub["date"], sub["avg_weight"], marker="s", color="tab:orange", label="avg weight")
        ax2.set_ylabel("avg weight (kg)", color="tab:orange")
        ax2.tick_params(axis="y", labelcolor="tab:orange")
        try:
            from matplotlib.ticker import MaxNLocator
            from matplotlib.dates import DateFormatter, AutoDateLocator

            ax1.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax2.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax1.xaxis.set_major_locator(AutoDateLocator())
            ax1.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
            for lbl in ax1.get_xticklabels():
                lbl.set_rotation(30)
                lbl.set_ha("right")
        except Exception:
            pass

        title = ex_map.get(int(ex_id), f"exercise_{ex_id}")
        fig.suptitle(f"{title} (id={ex_id})")

        # legend
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines + lines2, labels + labels2, loc="upper left", fontsize="small")

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        fname = OUT_DIR / f"exercise_{ex_id}_{sanitize(title)}.png"
        fig.savefig(fname, dpi=150)
        plt.close(fig)
        print("written", fname)


if __name__ == "__main__":
    main()
