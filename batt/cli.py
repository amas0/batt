import time

import typer
from rich.console import Console

import batt.db as db
import batt.psu as psu
import batt.batt as batt

app = typer.Typer()
console = Console()
database = db.Database.load_default()


@app.command()
def save_battery_status():
    current_battery_info = psu.get_current_battery_info()
    timestamp = int(time.time())
    database.insert_battery_status(current_battery_info, timestamp)


@app.command()
def status(
    table: bool = typer.Option(
        False, "--table", "-t", help="Print status in table format"
    ),
):
    if table:
        console.print(batt.BatteryStatus.current().table)
    else:
        console.print(batt.BatteryStatus.current().rich)


if __name__ == "__main__":
    app()
