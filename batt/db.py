import os
import sqlite3
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from batt.psu import BatteryInfo
from batt.system_states import StateTransition

BATT_DB_PATH = Path(os.environ.get("BATT_DB_PATH", Path.home() / ".batt.db"))


@dataclass
class Column:
    name: str
    type: Literal["TEXT", "NUMERIC", "INTEGER", "REAL", "BLOB"]
    primary_key: bool = False
    nullable: bool = False
    autoincrement: bool = False

    @property
    def spec(self) -> str:
        statement = f"{self.name} {self.type}"
        if self.primary_key:
            statement = f"{statement} PRIMARY KEY"
            if self.autoincrement:
                statement = f"{statement} AUTOINCREMENT"
        elif not self.nullable:
            statement = f"{statement} NOT NULL"
        return statement


@dataclass
class Table:
    name: str
    columns: tuple[Column, ...]
    additional_statements: str = ""

    @property
    def create_statement(self) -> str:
        column_stmnts = ", ".join(col.spec for col in self.columns)
        if self.additional_statements:
            column_stmnts = f"{column_stmnts}, {self.additional_statements}"
        return f"CREATE TABLE IF NOT EXISTS {self.name} ({column_stmnts})"


class Database:
    BATTERY_INFO_TABLE = Table(
        "battery_info",
        (
            Column("id", "INTEGER", primary_key=True, autoincrement=True),
            Column("voltage_min_design", "INTEGER"),
            Column("energy_full_design", "INTEGER"),
            Column("model_name", "TEXT"),
            Column("manufacturer", "TEXT"),
            Column("serial_number", "TEXT"),
        ),
    )
    STATUS_TABLE = Table(
        "status",
        (
            Column("timestamp_utc", "INTEGER", primary_key=True),
            Column("info_id", "INTEGER"),
            Column("status", "INTEGER"),
            Column("voltage", "INTEGER"),
            Column("power", "INTEGER"),
            Column("energy_full", "INTEGER"),
            Column("energy_now", "INTEGER"),
        ),
        additional_statements=f"FOREIGN KEY(info_id) REFERENCES {BATTERY_INFO_TABLE.name}(id)",
    )
    SYSTEM_STATES_TABLE = Table(
        "system_state",
        (
            Column("timestamp", "INTEGER", primary_key=True),
            Column("initial_state", "INTEGER"),
            Column("final_state", "INTEGER"),
        ),
    )
    TABLES = (BATTERY_INFO_TABLE, STATUS_TABLE, SYSTEM_STATES_TABLE)

    def __init__(self, path: Path):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.initialize_tables()

    @classmethod
    def load_default(cls):
        return cls(BATT_DB_PATH)

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

    def turn_on_foreign_keys(self):
        with self.cursor() as cur:
            cur.execute("PRAGMA foreign_keys = ON")

    def insert_battery_status(self, info: BatteryInfo, timestamp: int):
        if (info_id := self.get_existing_battery_info_id(info)) is None:
            self.insert_battery_info(info)
            info_id = self.get_existing_battery_info_id(info)

        column_names = [col.name for col in self.STATUS_TABLE.columns]
        values = [
            timestamp,
            info_id,
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

    def get_existing_battery_info_id(self, info: BatteryInfo) -> int | None:
        """Assume that two batteries are the same if they have
        the same model_name + manufacturer + serial number"""
        stmt = (
            f"SELECT id FROM {self.BATTERY_INFO_TABLE.name} WHERE "
            f"model_name = ? AND manufacturer = ? and serial_number = ?"
        )
        params = (info.model_name, info.manufacturer, info.serial_number)
        with self.cursor() as cur:
            cur.execute(stmt, params)
            if result := cur.fetchone():
                return result[0]
            else:
                return None

    def insert_battery_info(self, info: BatteryInfo):
        column_names = [
            col.name for col in self.BATTERY_INFO_TABLE.columns if not col.autoincrement
        ]
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

    def insert_state_transition(self, st: StateTransition):
        column_names = [col.name for col in self.SYSTEM_STATES_TABLE.columns]
        values = [st.timestamp, st.initial.value, st.final.value]
        placeholders = ", ".join("?" * len(values))
        insert_stmt = (
            f"INSERT INTO {self.SYSTEM_STATES_TABLE.name} "
            f"({','.join(column_names)}) VALUES ({placeholders})"
        )
        with self.cursor() as cursor:
            cursor.execute(insert_stmt, values)
        self.conn.commit()
