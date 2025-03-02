import time
from datetime import datetime, timedelta

import typer
from rich.console import Console

import batt.db as db
import batt.psu as psu
import batt.proc as proc
import batt.batt as batt
import batt.system_states as system_states
import batt.backlight as backlight

app = typer.Typer()
console = Console()
database = db.Database.load_default()


@app.command()
def save_backlight_state():
    reading = backlight.get_backlight_reading()
    database.insert_backlight_reading(reading)


@app.command()
def save_battery_status():
    current_battery_info = psu.get_current_battery_info()
    timestamp = int(time.time())
    database.insert_battery_status(current_battery_info, timestamp)


@app.command()
def save_recent_state_transitions(
    since: datetime = typer.Argument(
        help="Add system state transitions starting from the provided date"
    ),
):
    recent_st = system_states.get_recent_system_state_transitions(since)
    for st in recent_st:
        database.insert_state_transition(st)


@app.command()
def save_proc_status():
    all_proc_stats = proc.get_all_proc_stats()
    for ps in all_proc_stats:
        database.insert_process_stat(ps)


@app.command()
def update_all():
    last_system_state_transition = database.most_recent_system_state()
    if last_system_state_transition is None:
        since = datetime.now() - timedelta(days=90)
    else:
        since = datetime.fromtimestamp(last_system_state_transition.timestamp + 1)

    save_battery_status()
    save_recent_state_transitions(since)
    save_backlight_state()
    save_proc_status()


@app.command()
def updater(
    interval: int = typer.Option(
        60, "--interval", "-i", help="Update interval (in seconds)"
    ),
):
    while True:
        update_all()
        time.sleep(interval)


@app.command()
def status(
    table: bool = typer.Option(
        False, "--table", "-t", help="Print status in table format"
    ),
    csv: bool = typer.Option(
        False,
        "--csv",
        "-c",
        help=(
            "Print battery status in CSV format. Output is charging "
            "status, power (mW), current energy (mWh), full energy (mWh)"
        ),
    ),
    timestamp: bool = typer.Option(
        False, "--timestamp", help="Prepend UNIX timestmap in CSV output"
    ),
):
    if csv:
        csv_vals = batt.BatteryStatus.current().csv
        if timestamp:
            ts = int(time.time())
            console.print(f"{ts},{csv_vals}")
        else:
            console.print(csv_vals)
    elif table:
        console.print(batt.BatteryStatus.current().table)
    else:
        console.print(batt.BatteryStatus.current().rich)


if __name__ == "__main__":
    app()
