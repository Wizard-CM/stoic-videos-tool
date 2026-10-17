"""Is a worker process still running? Works on macOS, Linux and Windows without extra packages."""

import os
import sys
from multiprocessing.process import BaseProcess

# Processes this server started. Asking them directly also cleans up finished ("zombie") children.
started_processes: dict[int, BaseProcess] = {}

WINDOWS_STILL_ACTIVE = 259
WINDOWS_QUERY_LIMITED_INFORMATION = 0x1000


def remember_process(process: BaseProcess) -> None:
    started_processes[process.pid] = process


def _windows_pid_is_running(pid: int) -> bool:
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(WINDOWS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    exit_code = ctypes.c_ulong()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
    kernel32.CloseHandle(handle)
    return exit_code.value == WINDOWS_STILL_ACTIVE


def pid_is_running(pid: int) -> bool:
    if pid in started_processes:
        return started_processes[pid].is_alive()
    if sys.platform == "win32":
        return _windows_pid_is_running(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
