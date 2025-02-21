from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessStat:
    pid: int
    command: str
    utime: int
    stime: int
    cutime: int
    cstime: int


def get_proc_pid_stat_files():
    proc_dirs = Path("/proc/").iterdir()
    stat_files = []
    for pd in proc_dirs:
        if pd.is_dir() and pd.parts[-1].isdigit():
            if (pd / "stat").exists():
                stat_files.append(pd / "stat")
    return stat_files


def parse_pid_stat_file(file: Path) -> ProcessStat:
    with open(file, "r") as f:
        fields = f.read().strip().split()
    name = fields[1].strip("()")
    return ProcessStat(int(fields[0]), name, *map(int, fields[13:17]))
