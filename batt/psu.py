from enum import Enum
from pathlib import Path
from dataclasses import dataclass


class LowLevelBatteryStatus(Enum):
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
    """Battery information parsed from /sys/class/power_supply/BAT0

    Units for voltage, power, and energy are microvolts, microwatts,
    and microwatt-hours, respectively"""

    name: str
    status: LowLevelBatteryStatus
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
    """Parses /sys/class/power_supply/BAT0/uevent for current battery info"""
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
        status=LowLevelBatteryStatus.from_value(parsed["STATUS"]),
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


def desmooth_power_reading(current: int, prior: int, alpha: float = 0.1365):
    """Experiments on my laptop have shown that the power readings as reported
    by the battery are exponentially smoothed. For a given smoothing parameter
    alpha, and a reading x[t] at time t, the smoothed value S[t] is given
    by:

    S[t] = alpha * x[t] + (1 - alpha) * S[t-1]

    Then by sequential readings of the smoothed value (and an estimate of
    the smoothing parameter, we can recover the "true" reading x[t].

    This function does so and uses a default smoothing value based on
    experiments.
    """
    return (current - (1 - alpha) * prior) / alpha
