from pathlib import Path
import argparse
from datetime import date
from typing import List, Any

import pandas as pd

from data_connection import load_table, open_duckdb

def _parse_list_ints(s: str) -> List[int]:
    s = (s or "").strip()
    if not s:
        return []
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def _parse_list_floats(s: str) -> List[float]:
    s = (s or "").strip()
    if not s:
        return []
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def choose_workout(workouts_df: pd.DataFrame) -> Any:
    if workouts_df is None or workouts_df.empty:
        print("No workouts found in DB.")
        return None
    print("Available workouts:")
    for row in workouts_df.to_dict(orient="records"):
        print(f"  {int(row['id'])}: {row.get('name','')}")
    while True:
        sel = input("Select workout id: ").strip()
        if not sel:
            return None
        try:
            wid = int(sel)
        except ValueError:
            print("Enter a numeric id.")
            continue
        matches = workouts_df[workouts_df["id"].astype(int) == wid]
        if matches.empty:
            print("Unknown workout id.")
            continue
        return matches.iloc[0].to_dict()


def main():
    p = argparse.ArgumentParser(description="Record performance for a workout")
    p.add_argument("--workout-id", type=int, help="optional workout id to select directly")
    args = p.parse_args()

    # load workouts and exercises
    try:
        workouts_df = load_table("workouts")
    except Exception:
        workouts_df = pd.DataFrame()
    try:
        exercises_df = load_table("exercises")
    except Exception:
        exercises_df = pd.DataFrame()

    selected = None
    if args.workout_id is not None:
        if workouts_df is None or workouts_df.empty:
            print("No workouts available.")
            return
        matches = workouts_df[workouts_df["id"].astype(int) == int(args.workout_id)]
        if matches.empty:
            print(f"Workout id {args.workout_id} not found.")
            return
        selected = matches.iloc[0].to_dict()
    else:
        selected = choose_workout(workouts_df)
        if selected is None:
            print("Aborted.")
            return

    # extract exercise ids from workout (ensure ints)
    ex_ids = selected.get("exercises")
    ex_ids = [int(i) for i in ex_ids]

    # date
    d_in = input(f"Date (YYYY-MM-DD) [default {date.today().isoformat()}]: ").strip()
    if not d_in:
        used_date = date.today().isoformat()
    else:
        used_date = d_in

    rows = []
    for ex_id in ex_ids:
        ex_row = None
        if exercises_df is not None and not exercises_df.empty:
            found = exercises_df[exercises_df["id"].astype(int) == ex_id]
            if not found.empty:
                ex_row = found.iloc[0].to_dict()

        ex_name = ex_row.get("name") if ex_row else f"#{ex_id}"
        print(f"\nExercise {ex_id}: {ex_name}")

        # ask for reps (comma separated for sets)
        reps_input = input("  Reps (comma-separated for sets). Leave blank to mark 'finished earlier': ").strip()
        reps_list = _parse_list_ints(reps_input)
        if not reps_list:
            reps_list = []
        
        # ask for weights (comma separated). default 0 for blanks
        if len(reps_list) == 0:
            weights_list = []
        else:
            weights_input = input("  Weights (kg) per set (comma-separated). Leave blank = 0: ").strip()
            weights_list = _parse_list_floats(weights_input)
        
        # if user provided single weight but multiple sets, replicate
        if reps_list and len(weights_list) == 1 and len(reps_list) > 1:
            weights_list = weights_list * len(reps_list)
        # if weights longer than reps, trim; if shorter, pad with 0s
        if reps_list:
            if len(weights_list) > len(reps_list):
                weights_list = weights_list[: len(reps_list)]
            elif len(weights_list) < len(reps_list):
                weights_list = weights_list + [0.0] * (len(reps_list) - len(weights_list))

        rows.append(
            {
                "workout_id": int(selected["id"]),
                "exercise_id": int(ex_id),
                "date": used_date,
                "reps": reps_list,
                "weights": weights_list,
            }
        )

    if not rows:
        print("No performance recorded.")
        return

    new_df = pd.DataFrame(rows)

    # write into DuckDB (create if missing, otherwise insert)
    with open_duckdb() as conn:
        conn.register("perf_df", new_df)
        exists = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='performance'"
        ).fetchone()[0]
        if exists:
            conn.execute("INSERT INTO performance SELECT * FROM perf_df")
        else:
            conn.execute("CREATE TABLE performance AS SELECT * FROM perf_df")

    print(f"Wrote {len(new_df)} performance rows to DB.")


if __name__ == "__main__":
    main()
