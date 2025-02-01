import sqlite3
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from acpi import BatteryStatusReading, BatteryDesignInfo


@dataclass
class Column:
    name: str
    type: Literal["TEXT", "NUMERIC", "INTEGER", "REAL", "BLOB"]
    primary_key: bool = False
    nullable: bool = False

    @property
    def spec(self) -> str:
        statement = f"{self.name} {self.type}"
        if self.primary_key:
            statement = f"{statement} NOT NULL"
        elif self.nullable:
            statement = f"{statement} PRIMARY KEY"
        return statement


@dataclass
class Table:
    name: str
    columns: list[Column]

    @property
    def create_statement(self) -> str:
        column_stms = ", ".join(col.spec for col in self.columns)
        return f"CREATE TABLE IF NOT EXISTS {self.name} ({column_stms})"


class Database:
    TABLES = [
        Table(
            "status",
            [
                Column("timestamp_utc", "INTEGER", True),
                Column("state", "INTEGER"),
                Column("percentage", "INTEGER"),
                Column("minutes_until_discharged", "INTEGER"),
                Column("minutes_until_charged", "INTEGER"),
            ],
        ),
        Table(
            "design_info",
            [
                Column("timestamp_utc", "INTEGER", True),
                Column("design_capacity_mah", "INTEGER"),
                Column("last_full_capacity_mah", "INTEGER"),
            ],
        ),
    ]

    def __init__(self, path: Path):
        self.path = path
        self.conn = sqlite3.connect(self.path)

    @contextmanager
    def cursor(self):
        cursor = self.conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def initialize_tables(self):
        with self.cursor() as cur:
            for table in Database.TABLES:
                cur.execute(table.create_statement)
