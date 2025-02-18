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

    @classmethod
    def from_values(cls, ts: int, init: int, final: int):
        """Instantiates a StateTransition object from the values of timestamp,
        initial state, and final state"""
        init_enum = SystemState(init)
        final_enum = SystemState(final)
        return cls(ts, init_enum, final_enum)


def get_recent_suspend_transitions(since: datetime) -> list[StateTransition]:
    """Extract transitions between sleep and wake from journalctl events"""

    def parse_out_dt(line: str) -> datetime:
        return datetime.fromtimestamp(float(line.split()[0]))

    command = [
        "journalctl",
        "-S",
        f"{since.isoformat()}",
        "-o",
        "short-unix",
        "-g",
        "suspend e",
    ]
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


def get_recent_hibernate_transitions(since: datetime) -> list[StateTransition]:
    """Extract hibernate transitions from journalctl events"""

    def parse_out_dt(line: str) -> datetime:
        return datetime.fromtimestamp(float(line.split()[0]))

    command = [
        "journalctl",
        "-S",
        f"{since.isoformat()}",
        "-o",
        "short-unix",
        "-g",
        "sleep operation 'hibernate",
    ]
    out = subprocess.run(command, capture_output=True)
    lines = out.stdout.decode().split("\n")
    transitions = []
    for line in lines:
        if "Performing sleep operation" in line:
            dt = parse_out_dt(line)
            transitions.append(
                StateTransition(
                    int(dt.timestamp()), SystemState.ON, SystemState.HIBERNATE
                )
            )
        elif "System returned from" in line:
            dt = parse_out_dt(line)
            transitions.append(
                StateTransition(
                    int(dt.timestamp()), SystemState.HIBERNATE, SystemState.ON
                )
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

    transitions = sorted(
        [
            st
            for rec in boot_records
            for st in parse_transitions(rec)
            if st.timestamp >= since.timestamp()
        ],
        key=lambda tr: tr.timestamp,
    )
    # Check to remove the most recent entry as it is likely the current
    # ongoing boot session, otherwise we erroneously report the system
    # as being turned off when the sesion is ongoing
    if (transitions[-1].final == SystemState.OFF) and (
        transitions[-1].initial == SystemState.ON
    ):
        transitions = transitions[:-1]
    return transitions


def get_recent_system_state_transitions(since: datetime) -> list[StateTransition]:
    sleeps = get_recent_suspend_transitions(since)
    boots = get_recent_boot_and_shutdown_transitions(since)
    hibernates = get_recent_hibernate_transitions(since)
    return sleeps + boots + hibernates
