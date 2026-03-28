"""
Extraction pipeline DB adapter.

This module bridges Extraction_pipeline's Supabase-style table API to the
shared SQLAlchemy session defined in models/database.py.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import text

from models.database import SessionLocal

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(name: str) -> str:
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name}")
    return name


def _normalize_value(value: Any) -> Any:
    return getattr(value, "value", value)


@dataclass
class QueryResult:
    data: Any = None


class StorageBucketAdapter:
    def __init__(self, bucket: str):
        self.bucket = bucket

    def upload(self, key: str, payload: bytes):
        from main import supabase_admin

        if supabase_admin is None:
            raise RuntimeError("Supabase storage client is not configured")
        return supabase_admin.storage.from_(self.bucket).upload(key, payload)

    def download(self, key: str):
        from main import supabase_admin

        if supabase_admin is None:
            raise RuntimeError("Supabase storage client is not configured")
        return supabase_admin.storage.from_(self.bucket).download(key)

    def get_public_url(self, key: str):
        from main import supabase_admin

        if supabase_admin is None:
            raise RuntimeError("Supabase storage client is not configured")
        return supabase_admin.storage.from_(self.bucket).get_public_url(key)


class StorageAdapter:
    def from_(self, bucket: str) -> StorageBucketAdapter:
        _safe_identifier(bucket)
        return StorageBucketAdapter(bucket)


class TableQuery:
    def __init__(self, table_name: str):
        self.table_name = _safe_identifier(table_name)
        self._mode: str | None = None
        self._select_cols = "*"
        self._filters: list[tuple[str, str, Any]] = []
        self._order_by: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._single = False
        self._insert_payload: dict[str, Any] | None = None
        self._update_payload: dict[str, Any] | None = None

    def select(self, columns: str):
        self._mode = "select"
        columns = columns.strip()
        if columns != "*":
            parsed = []
            for col in columns.split(","):
                col_name = _safe_identifier(col.strip())
                parsed.append(col_name)
            self._select_cols = ", ".join(parsed)
        else:
            self._select_cols = "*"
        return self

    def eq(self, field: str, value: Any):
        self._filters.append(("eq", _safe_identifier(field), _normalize_value(value)))
        return self

    def in_(self, field: str, values: list[Any]):
        normalized = [_normalize_value(v) for v in list(values)]
        self._filters.append(("in", _safe_identifier(field), normalized))
        return self

    def order(self, field: str, desc: bool = False):
        self._order_by = _safe_identifier(field)
        self._order_desc = bool(desc)
        return self

    def limit(self, count: int):
        self._limit = int(count)
        return self

    def single(self):
        self._single = True
        return self

    def insert(self, payload: dict[str, Any]):
        self._mode = "insert"
        self._insert_payload = payload
        return self

    def update(self, payload: dict[str, Any]):
        self._mode = "update"
        self._update_payload = payload
        return self

    def execute(self) -> QueryResult:
        if self._mode == "select":
            return self._execute_select()
        if self._mode == "insert":
            return self._execute_insert()
        if self._mode == "update":
            return self._execute_update()
        raise ValueError("No query mode set. Use select/insert/update before execute().")

    def _build_where(self) -> tuple[str, dict[str, Any]]:
        if not self._filters:
            return "", {}

        clauses: list[str] = []
        params: dict[str, Any] = {}
        idx = 0

        for op, field, value in self._filters:
            if op == "eq":
                key = f"w_{idx}"
                clauses.append(f"{field} = :{key}")
                params[key] = value
                idx += 1
            elif op == "in":
                in_values = value or []
                if not in_values:
                    clauses.append("1=0")
                    continue
                placeholders = []
                for v in in_values:
                    key = f"w_{idx}"
                    placeholders.append(f":{key}")
                    params[key] = v
                    idx += 1
                clauses.append(f"{field} IN ({', '.join(placeholders)})")

        return f" WHERE {' AND '.join(clauses)}", params

    def _execute_select(self) -> QueryResult:
        where_sql, params = self._build_where()
        sql = f"SELECT {self._select_cols} FROM {self.table_name}{where_sql}"

        if self._order_by:
            direction = "DESC" if self._order_desc else "ASC"
            sql += f" ORDER BY {self._order_by} {direction}"
        if self._limit is not None:
            sql += " LIMIT :limit_count"
            params["limit_count"] = self._limit

        with SessionLocal() as db:
            rows = db.execute(text(sql), params).mappings().all()

        data = [dict(row) for row in rows]
        if self._single:
            return QueryResult(data=data[0] if data else None)
        return QueryResult(data=data)

    def _execute_insert(self) -> QueryResult:
        payload = self._insert_payload or {}
        if not payload:
            raise ValueError("Insert payload cannot be empty")

        columns = [_safe_identifier(c) for c in payload.keys()]
        params = {f"v_{idx}": payload[col] for idx, col in enumerate(payload.keys())}
        params = {k: _normalize_value(v) for k, v in params.items()}
        placeholders = [f":v_{idx}" for idx in range(len(columns))]
        sql = (
            f"INSERT INTO {self.table_name} ({', '.join(columns)}) "
            f"VALUES ({', '.join(placeholders)})"
        )

        with SessionLocal() as db:
            db.execute(text(sql), params)
            db.commit()

        return QueryResult(data=payload)

    def _execute_update(self) -> QueryResult:
        payload = self._update_payload or {}
        if not payload:
            raise ValueError("Update payload cannot be empty")

        set_parts = []
        params: dict[str, Any] = {}
        for idx, (col, value) in enumerate(payload.items()):
            safe_col = _safe_identifier(col)
            key = f"s_{idx}"
            set_parts.append(f"{safe_col} = :{key}")
            params[key] = value
            params[key] = _normalize_value(params[key])

        where_sql, where_params = self._build_where()
        params.update(where_params)

        sql = f"UPDATE {self.table_name} SET {', '.join(set_parts)}{where_sql}"

        with SessionLocal() as db:
            db.execute(text(sql), params)
            db.commit()

        return QueryResult(data=payload)


class SQLDatabaseAdapter:
    def __init__(self):
        self.storage = StorageAdapter()

    def table(self, table_name: str) -> TableQuery:
        return TableQuery(table_name)


def get_google_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise EnvironmentError("GOOGLE_API_KEY (or GEMINI_API_KEY) must be set in environment.")
    return key


@lru_cache(maxsize=1)
def get_supabase() -> SQLDatabaseAdapter:
    return SQLDatabaseAdapter()
