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
    columns: tuple[Column, ...]

    @property
    def create_statement(self) -> str:
        column_stms = ", ".join(col.spec for col in self.columns)
        return f"CREATE TABLE IF NOT EXISTS {self.name} ({column_stms})"


class Database:
    STATUS_TABLE = Table(
        "status",
        (
            Column("timestamp_utc", "INTEGER", True),
            Column("state", "INTEGER"),
            Column("percentage", "INTEGER"),
            Column("minutes_until_discharged", "INTEGER"),
            Column("minutes_until_charged", "INTEGER"),
        ),
    )
    DESIGN_INFO_TABLE = Table(
        "design_info",
        (
            Column("timestamp_utc", "INTEGER", True),
            Column("design_capacity_mah", "INTEGER"),
            Column("last_full_capacity_mah", "INTEGER"),
        ),
    )
    TABLES = (STATUS_TABLE, DESIGN_INFO_TABLE)

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

    def insert_battery_status(self, status: BatteryStatusReading):
        column_names = [col.name for col in self.STATUS_TABLE.columns]
        values = [
            status.timestamp_utc,
            status.state.value,
            status.percentage,
            status.minutes_until_discharged,
            status.minutes_until_charged,
        ]
        placeholders = ", ".join("?" * len(values))
        insert_stmt = f"INSERT INTO {self.STATUS_TABLE.name} ({','.join(column_names)}) VALUES ({placeholders})"
        with self.cursor() as cursor:
            cursor.execute(insert_stmt, values)
        self.conn.commit()

    def insert_battery_design_info(self, design: BatteryDesignInfo):
        column_names = [col.name for col in self.DESIGN_INFO_TABLE.columns]
        values = [
            design.timestamp_utc,
            design.design_capacity_mah,
            design.last_full_capacity_mah,
        ]
        placeholders = ", ".join("?" * len(values))
        insert_stmt = f"INSERT INTO {self.DESIGN_INFO_TABLE.name} ({','.join(column_names)}) VALUES ({placeholders})"
        with self.cursor() as cursor:
            cursor.execute(insert_stmt, values)
        self.conn.commit()
