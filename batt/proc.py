import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessStat:
    timestamp: int
    pid: int
    ppid: int
    command: str
    utime: int
    stime: int
    cutime: int
    cstime: int

    @property
    def total(self) -> int:
        return self.utime + self.stime + self.cutime + self.cstime


def get_proc_pid_stat_files():
    proc_dirs = Path("/proc/").iterdir()
    stat_files = []
    for pd in proc_dirs:
        if pd.is_dir() and pd.parts[-1].isdigit():
            if (pd / "stat").exists():
                stat_files.append(pd / "stat")
    return stat_files


def parse_pid_stat_file(file: Path, timestamp: int) -> ProcessStat:
    with open(file, "r") as f:
        fields = f.read().strip().split()
    name = fields[1].strip("()")
    ppid = int(fields[3])
    return ProcessStat(timestamp, int(fields[0]), ppid, name, *map(int, fields[13:17]))


def get_all_proc_stats() -> list[ProcessStat]:
    files = get_proc_pid_stat_files()
    ts = int(time.time())
    all_proc_stats = [parse_pid_stat_file(file, ts) for file in files]
    return all_proc_stats
