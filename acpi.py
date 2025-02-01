import re
import subprocess
import time
from dataclasses import dataclass
from enum import Enum


class BatteryState(Enum):
    charging = 1
    discharging = 2
    full = 3


@dataclass
class BatteryStatusReading:
    timestamp_utc: int
    state: BatteryState
    percentage: int
    minutes_until_discharged: int | None
    minutes_until_charged: int | None

    @staticmethod
    def extract_estimated_minutes(time_str: str) -> int:
        pat = r"(?:(\d{2}):(\d{2}):(\d{2}))"
        found = re.findall(pat, time_str)
        if not found:
            raise ValueError(f"Unable to parse time estimation from {time_str}")
        (h, m, s), *_ = found
        est_min = int(m) + round(int(s) / 60)
        if h:
            est_min += int(h) * 60
        return est_min

    @classmethod
    def from_acpi_output(cls, status: str, timestamp: int):
        pat = r"Battery \d+: (\w+), (\d+)%, (.*)"
        match = re.match(pat, status)
        if not match:
            raise ValueError("Parsing ACPI status failed")
        s, p, r = match.groups()
        match s.lower():
            case "charging":
                state = BatteryState.charging
            case "discharging":
                state = BatteryState.discharging
            case "full":
                state = BatteryState.full
            case _:
                raise ValueError(f"Unable to parse state from: {s}")

        percentage = int(p)
        status_kwargs = dict(
            timestamp_utc=timestamp,
            state=state,
            percentage=percentage,
            minutes_until_discharged=None,
            minutes_until_charged=None,
        )
        if state == BatteryState.charging:
            status_kwargs["minutes_until_charged"] = cls.extract_estimated_minutes(r)
        elif state == BatteryState.discharging:
            status_kwargs["minutes_until_discharged"] = cls.extract_estimated_minutes(r)
        return cls(**status_kwargs)  # type: ignore


@dataclass
class BatteryDesignInfo:
    timestamp_utc: int
    design_capacity_mah: int
    last_full_capacity_mah: int

    @classmethod
    def from_acpi_output(cls, design: str, timestamp: int):
        pat = r"Battery \d+: design capacity (\d+) mAh, last full capacity (\d+) mAh"
        match = re.match(pat, design)
        if not match:
            raise ValueError(f"Unable to parse battery design info from {design}")
        des, lfc = match.groups()
        return cls(
            timestamp_utc=timestamp,
            design_capacity_mah=int(des),
            last_full_capacity_mah=int(lfc),
        )

    @property
    def last_full_capacity_perc(self):
        return self.last_full_capacity_mah / self.design_capacity_mah


def read_battery_info() -> tuple[BatteryStatusReading, BatteryDesignInfo]:
    """Reads battery status and design information from acpi and returns
    structured BatteryStatusReading and BatteryDesignInfo objects"""
    cmd_stdout = subprocess.run(["acpi", "-i"], capture_output=True).stdout.decode()
    timestamp = int(time.time())
    status_line, design_line, *_ = cmd_stdout.split("\n")
    return BatteryStatusReading.from_acpi_output(
        status_line, timestamp
    ), BatteryDesignInfo.from_acpi_output(design_line, timestamp)
