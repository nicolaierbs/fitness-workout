"""
Simple utilities to open a DuckDB database file and read tables.

Usage examples:
from duckdb_loader import open_duckdb, connect_duckdb, load_table_as_df

with open_duckdb("data/my.db", read_only=True) as conn:
    df = load_table_as_df(conn, "workouts")
"""
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union, Iterator

import duckdb
import pandas as pd

# use project data dir by default
db_path = Path(__file__).resolve().parent.parent / "data" / "fitness.db"


def connect_duckdb(database: Optional[Union[str, Path]] = None, pragmas: Optional[dict] = None) -> duckdb.DuckDBPyConnection:
    """
    Connect to a DuckDB file and return a connection.

    - database: path to the .db file (if None uses module-level db_path).
    - pragmas: optional dict of PRAGMA name -> value to set on the connection.

    Caller is responsible for closing the returned connection.
    """
    database = Path(database) if database is not None else db_path
    conn = duckdb.connect(database=str(database))
    if pragmas:
        for k, v in pragmas.items():
            conn.execute(f"PRAGMA {k}={v}")
    return conn


@contextmanager
def open_duckdb(database: Optional[Union[str, Path]] = None, pragmas: Optional[dict] = None) -> Iterator[duckdb.DuckDBPyConnection]:
    """
    Context manager that yields a DuckDB connection and closes it after use.
    """
    conn = connect_duckdb(database=database, pragmas=pragmas)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def load_table_as_df(conn: duckdb.DuckDBPyConnection, table: str) -> pd.DataFrame:
    """
    Load an entire table (or query alias) into a pandas DataFrame.

    Example:
        df = load_table_as_df(conn, "workouts")
    """
    return conn.execute(f"SELECT * FROM {table}").df()


def query_df(conn: duckdb.DuckDBPyConnection, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """
    Execute a SQL query and return a pandas DataFrame. Optionally pass params as a tuple.
    """
    if params:
        return conn.execute(sql, params).df()
    return conn.execute(sql).df()


def load_table(table: str, database: Optional[Union[str, Path]] = None, pragmas: Optional[dict] = None) -> pd.DataFrame:
    """
    Convenience: open the DB, read a table into a DataFrame and close the connection.
    """
    with open_duckdb(database=database, pragmas=pragmas) as conn:
        return load_table_as_df(conn, table)
