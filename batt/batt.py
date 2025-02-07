from dataclasses import dataclass
from typing import Literal

from rich import box
from rich.text import Text
from rich.table import Table

import batt.psu as psu


@dataclass
class BatteryStatus:
    status: Literal["Charging", "Discharging", "Full", "Not Charging", "Unknown"]
    energy_full: int
    energy_now: int
    power_now: int

    @classmethod
    def current(cls):
        info = psu.get_current_battery_info()
        match info.status:
            case psu.LowLevelBatteryStatus.Charging:
                status_str = "Charging"
            case psu.LowLevelBatteryStatus.Discharging:
                status_str = "Discharging"
            case psu.LowLevelBatteryStatus.Full:
                status_str = "Full"
            case psu.LowLevelBatteryStatus.NotCharging:
                status_str = "Not Charging"
            case _:
                status_str = "Unknown"
        return cls(
            status=status_str,
            energy_full=info.energy_full // 1000,
            energy_now=info.energy_now // 1000,
            power_now=info.power_now // 1000,
        )

    @property
    def percentage(self) -> float:
        return 100 * self.energy_now / self.energy_full

    def hours_until_discharged(self) -> float | None:
        if self.status == "Discharging":
            return self.energy_now / self.power_now

    def hours_until_charged(self) -> float | None:
        if self.status == "Full":
            return 0
        if self.status == "Charging":
            return (self.energy_full - self.energy_now) / self.power_now

    @property
    def table(self):
        table = Table(
            show_header=False, show_edge=False, show_lines=False, box=box.MINIMAL
        )
        table.add_column("Item", style="grey70")
        table.add_column("Value", justify="right", style="bold")
        status_color = {
            "Charging": "green",
            "Full": "bold green",
            "Discharging": "yellow",
        }
        table.add_row(
            "Status", Text(self.status, style=status_color.get(self.status, "default"))
        )
        current_watts = self.power_now / 1000
        sign = "+" if self.status == "Charging" else "-"
        table.add_row("Power", f"{sign}{current_watts:.01f}W")
        if self.status == "Charging":
            hrs_float = (self.energy_full - self.energy_now) / self.power_now
            h = int(hrs_float)
            m = int(60 * (hrs_float - h))
            time = f"{h}:{m:02}"
            table.add_row("Time until charged", time)
        elif self.status == "Discharging":
            hrs_float = self.energy_now / self.power_now
            h = int(hrs_float)
            m = int(60 * (hrs_float - h))
            time = f"{h}:{m:02}"
            table.add_row("Time until empty", time)
        else:
            time = ""

        return table

    @property
    def rich(self):
        status_color = {
            "Charging": "green",
            "Full": "bold green",
            "Discharging": "yellow",
        }
        current_watts = self.power_now / 1000
        if self.status == "Charging":
            hrs_float = (self.energy_full - self.energy_now) / self.power_now
            h = int(hrs_float)
            m = int(60 * (hrs_float - h))
            time = f"{h}:{m:02}"
            target_status = "fully charge"
        elif self.status == "Discharging":
            hrs_float = self.energy_now / self.power_now
            h = int(hrs_float)
            m = int(60 * (hrs_float - h))
            time = f"{h}:{m:02}"
            target_status = "empty"
        else:
            time = ""
            target_status = ""

        status_text = Text(
            self.status.lower(), style=status_color.get(self.status, "default")
        )
        power_text = Text(f"{current_watts:.01f}W", style="bold")
        time_text = Text(f"{time}", style="bold")
        out = (
            Text(f"Battery is ")
            + status_text
            + Text(" at ")
            + power_text
            + Text(f" and estimated to {target_status} in ")
            + time_text
        )

        return out
