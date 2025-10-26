from data_connection import connect_duckdb, query_df
from pathlib import Path
import yaml
import pandas as pd
from typing import Optional, Union

DEFAULT_YAML = Path(__file__).resolve().parent.parent / "data" / "exercises.yaml"
DEFAULT_WORKOUT_YAML = Path(__file__).resolve().parent.parent / "data" / "workout.yaml"


def load_exercises_df(yaml_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """
    Load exercises YAML and return a normalized pandas DataFrame.
    """
    yaml_path = Path(yaml_path) if yaml_path is not None else DEFAULT_YAML
    with open(yaml_path, "r", encoding="utf-8") as f:
        exercises = yaml.safe_load(f)

    df = pd.DataFrame(exercises or [])

    if not df.empty and "reps" in df.columns:
        df["reps_min"] = df["reps"].apply(
            lambda r: int(r[0]) if isinstance(r, (list, tuple)) and len(r) > 0 else None
        )
        df["reps_max"] = df["reps"].apply(
            lambda r: int(r[1]) if isinstance(r, (list, tuple)) and len(r) > 1 else None
        )
        df["reps"] = df["reps"].apply(lambda r: list(r) if r is not None else None)

    return df


def load_workouts_df(yaml_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """
    Load workout YAML and return a normalized pandas DataFrame.
    Expects items with fields: id, exercises (list of ids), paired_sets (list of tuples/lists), comment.
    """
    yaml_path = Path(yaml_path) if yaml_path is not None else DEFAULT_WORKOUT_YAML
    with open(yaml_path, "r", encoding="utf-8") as f:
        workouts = yaml.safe_load(f)

    df = pd.DataFrame(workouts or [])

    # Ensure exercises and paired_sets are lists (Pandas will keep them as object dtype)
    if not df.empty:
        if "exercises" in df.columns:
            df["exercises"] = df["exercises"].apply(lambda v: list(v) if v is not None else [])
        if "paired_sets" in df.columns:
            df["paired_sets"] = df["paired_sets"].apply(
                lambda v: [list(t) for t in v] if v is not None else []
            )

    return df


def load_into_duckdb(
    loader,
    yaml_path: Optional[Union[str, Path]] = None
) -> None:
    """
    Generic loader: call `loader(yaml_path)` to get a DataFrame and write it into DuckDB as `table_name`.

    - loader: callable like load_exercises_df or load_workouts_df
    - yaml_path: optional path passed to the loader
    """
    
    conn = connect_duckdb()
    
    df = loader(yaml_path)
    
    # Extract the table path name from the loader name by removing 'load_' prefix and '_df' suffix
    loader_name = loader.__name__
    if loader_name.startswith("load_") and loader_name.endswith("_df"):
        table_name = loader_name[len("load_") : -len("_df")]
    else:
        table_name = "data_table"
    
    register_name = f"temp_{table_name}_df"
    conn.register(register_name, df)
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM {register_name}")

    try:
        conn.close()
    except Exception:
        pass


if __name__ == "__main__":
    # Run as script to populate the default DB with exercises and workouts
    load_into_duckdb(load_exercises_df)
    load_into_duckdb(load_workouts_df)
