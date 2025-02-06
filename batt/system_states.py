import subprocess
from dataclasses import dataclass
from datetime import datetime
from dateutil import parser
from enum import Enum


class SystemState(Enum):
    OFF = 1
    SLEEP = 2
    HIBERNATE = 3
    ON = 4


@dataclass
class StateTransition:
    timestamp: int
    initial: SystemState
    final: SystemState


def get_recent_suspend_transitions(since: datetime) -> list[StateTransition]:
    """Extract transitions between sleep and wake from journalctl events"""

    # TODO: Figure out hibernate

    def parse_out_dt(line: str) -> datetime:
        return parser.parse(" ".join(line.split()[:3]))

    command = ["journalctl", "-S", f"{since.isoformat()}", "-g", "suspend e"]
    out = subprocess.run(command, capture_output=True)
    lines = out.stdout.decode().split("\n")
    transitions = []
    for line in lines:
        if "suspend entry" in line:
            dt = parse_out_dt(line)
            transitions.append(
                StateTransition(int(dt.timestamp()), SystemState.ON, SystemState.SLEEP)
            )
        elif "suspend exit" in line:
            dt = parse_out_dt(line)
            transitions.append(
                StateTransition(int(dt.timestamp()), SystemState.SLEEP, SystemState.ON)
            )
    return transitions


def get_recent_boot_and_shutdown_transitions(since: datetime) -> list[StateTransition]:
    """Extract transitions between boot and shutdown from journalctl events"""

    def parse_transitions(line: str) -> tuple[StateTransition, StateTransition]:
        parts = line.split()
        boot_dt_str = " ".join(parts[2:6])
        shutdown_dt_str = " ".join(parts[6:])
        boot_st = StateTransition(
            int(parser.parse(boot_dt_str).timestamp()), SystemState.OFF, SystemState.ON
        )
        shutdown_st = StateTransition(
            int(parser.parse(shutdown_dt_str).timestamp()),
            SystemState.ON,
            SystemState.OFF,
        )
        return boot_st, shutdown_st

    command = ["journalctl", "--list-boots"]
    out = subprocess.run(command, capture_output=True)
    boot_records = (l.strip() for l in out.stdout.decode().split("\n")[1:] if l.strip())

    return [
        st
        for rec in boot_records
        for st in parse_transitions(rec)
        if st.timestamp >= since.timestamp()
    ]


def get_recent_system_state_transitions(since: datetime) -> list[StateTransition]:
    sleeps = get_recent_suspend_transitions(since)
    boots = get_recent_boot_and_shutdown_transitions(since)
    return sleeps + boots
