"""
database.py
===========
SQLite helpers used by (a) the pipeline, (b) the SQL playground page and
(c) the PDF report generator.

* build_database(df)        creates data/real_estate.db with one table
* run_query(sql, db_path)   executes a READ-ONLY query safely
* parse_sql_library(path)   turns the annotated .sql file into a dict
"""
from __future__ import annotations

import re
import sqlite3

import pandas as pd

from . import config as C

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|reindex)\b", re.I)


def build_database(df: pd.DataFrame, db_path=C.DB_PATH) -> None:
    """(Re)create the SQLite DB with a `properties` table and useful indexes."""
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    df.to_sql("properties", con, index=False, chunksize=50_000)
    for col in ("State", "City", "Locality", "Property_Type", "BHK", "Good_Investment"):
        con.execute(f'CREATE INDEX idx_{col} ON properties("{col}")')
    con.commit()
    con.close()


def validate_readonly(sql: str) -> str:
    """Allow a single SELECT / WITH statement only. Returns cleaned SQL."""
    cleaned = re.sub(r"--.*", "", sql).strip().rstrip(";").strip()
    if ";" in cleaned:
        raise ValueError("Only one statement can be run at a time.")
    if not re.match(r"^(select|with)\b", cleaned, re.I):
        raise ValueError("Only SELECT / WITH queries are allowed in the playground.")
    if FORBIDDEN.search(cleaned):
        raise ValueError("This statement contains a keyword that is not allowed (read-only mode).")
    return cleaned


def run_query(sql: str, db_path=C.DB_PATH, max_rows: int = 5000) -> pd.DataFrame:
    """Run a validated read-only query (opened in read-only URI mode)."""
    cleaned = validate_readonly(sql)
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return pd.read_sql_query(f"SELECT * FROM ({cleaned}) LIMIT {int(max_rows)}", con)
    finally:
        con.close()


def parse_sql_library(path=C.SQL_FILE) -> list[dict]:
    """
    Parse the annotated SQL file. Each query is introduced by
        -- @id: Q06
        -- @section: Location
        -- @title: Average price per sq ft by state
        -- @insight: one-line business takeaway
    followed by the SQL text up to the next @id block.
    """
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^-- @id:\s*", text)[1:]
    library = []
    for block in blocks:
        head, _, body = block.partition("\n")
        meta = {"id": head.strip()}
        sql_lines = []
        for line in body.splitlines():
            m = re.match(r"-- @(section|title|insight):\s*(.*)", line)
            if m:
                meta[m.group(1)] = m.group(2).strip()
            elif not line.startswith("-- ====="):
                sql_lines.append(line)
        meta["sql"] = "\n".join(sql_lines).strip().rstrip(";") + ";"
        library.append(meta)
    return library
