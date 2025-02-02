import sqlite3
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from psu import BatteryInfo


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
            Column("timestamp_utc", "INTEGER", primary_key=True),
            Column("status", "INTEGER"),
            Column("voltage", "INTEGER"),
            Column("power", "INTEGER"),
            Column("energy_full", "INTEGER"),
            Column("energy_now", "INTEGER"),
        ),
    )
    BATTERY_INFO_TABLE = Table(
        "battery_info",
        (
            Column("id", "INTEGER", primary_key=True),
            Column("voltage_min_design", "INTEGER"),
            Column("energy_full_design", "INTEGER"),
            Column("model_name", "TEXT"),
            Column("manufacturer", "TEXT"),
            Column("serial_number", "TEXT"),
        ),
    )
    TABLES = (STATUS_TABLE, BATTERY_INFO_TABLE)

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

    def insert_battery_status(self, info: BatteryInfo, timestamp: int):
        column_names = [col.name for col in self.STATUS_TABLE.columns]
        values = [
            timestamp,
            info.status.value,
            # Convert units order of magnitude from micro- to mili-
            info.voltage_now // 1000,
            info.power_now // 1000,
            info.energy_full // 1000,
            info.energy_now // 1000,
        ]
        placeholders = ", ".join("?" * len(values))
        insert_stmt = (
            f"INSERT INTO {self.STATUS_TABLE.name} "
            f"({','.join(column_names)}) VALUES ({placeholders})"
        )
        with self.cursor() as cursor:
            cursor.execute(insert_stmt, values)
        self.conn.commit()

    def insert_battery_info(self, info: BatteryInfo):
        column_names = [col.name for col in self.BATTERY_INFO_TABLE.columns]
        values = [
            # Convert units order of magnitude from micro- to mili-
            info.voltage_min_design // 1000,
            info.energy_full_design // 1000,
            info.model_name,
            info.manufacturer,
            info.serial_number,
        ]
        placeholders = ", ".join("?" * len(values))
        insert_stmt = (
            f"INSERT INTO {self.BATTERY_INFO_TABLE.name} "
            f"({','.join(column_names)}) VALUES ({placeholders})"
        )
        with self.cursor() as cursor:
            cursor.execute(insert_stmt, values)
        self.conn.commit()
