from enum import Enum
from pathlib import Path
from dataclasses import dataclass


class BatteryStatus(Enum):
    Unknown = 0
    Charging = 1
    Discharging = 2
    NotCharging = 3
    Full = 4

    @classmethod
    def from_value(cls, value: str):
        match value.lower():
            case "unknown":
                return cls.Unknown
            case "charging":
                return cls.Charging
            case "discharging":
                return cls.Discharging
            case "not charging":
                return cls.NotCharging
            case "full":
                return cls.Full
            case _:
                return cls.Unknown


class CapacityLevel(Enum):
    Unknown = 0
    Critical = 1
    Low = 2
    Normal = 3
    High = 4
    Full = 5

    @classmethod
    def from_value(cls, value: str):
        match value.lower():
            case "unknown":
                return cls.Unknown
            case "critical":
                return cls.Critical
            case "low":
                return cls.Low
            case "normal":
                return cls.Normal
            case "high":
                return cls.High
            case "full":
                return cls.Full
            case _:
                return cls.Unknown


@dataclass(frozen=True)
class BatteryInfo:
    name: str
    status: BatteryStatus
    voltage_min_design: int
    voltage_now: int
    power_now: int
    energy_full_design: int
    energy_full: int
    energy_now: int
    capacity: int
    capacity_level: CapacityLevel
    model_name: str
    manufacturer: str
    serial_number: str


def get_current_battery_info():
    bat0_path = Path("/sys/class/power_supply/BAT0/")
    parsed = {}
    with open(bat0_path / "uevent", "r") as f:
        for line in f:
            if not line.startswith("POWER_SUPPLY"):
                continue
            key, val = line.split("=")
            name = key.removeprefix("POWER_SUPPLY_")
            parsed[name] = val.strip()

    return BatteryInfo(
        name=parsed["NAME"],
        status=BatteryStatus.from_value(parsed["STATUS"]),
        voltage_min_design=int(parsed["VOLTAGE_MIN_DESIGN"]),
        voltage_now=int(parsed["VOLTAGE_NOW"]),
        power_now=int(parsed["POWER_NOW"]),
        energy_full_design=int(parsed["ENERGY_FULL_DESIGN"]),
        energy_full=int(parsed["ENERGY_FULL"]),
        energy_now=int(parsed["ENERGY_NOW"]),
        capacity=int(parsed["CAPACITY"]),
        capacity_level=CapacityLevel.from_value(parsed["CAPACITY_LEVEL"]),
        model_name=parsed["MODEL_NAME"],
        manufacturer=parsed["MANUFACTURER"],
        serial_number=parsed["SERIAL_NUMBER"],
    )


get_current_battery_info()
