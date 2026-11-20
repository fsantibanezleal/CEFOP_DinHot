"""Opt a process out of Windows power throttling (EcoQoS), so a worker runs at the speed of its core.

On 2026-11-16 the benchmark's pool workers ran at about half a core on an idle machine (thread state Ready; 0.5 against
1.0 CPU-seconds per second after an opt-out by hand), which changes how many iterations a time-budgeted row gets. Windows
throttles the execution speed of a process it judges to be background work; ``SetProcessInformation`` with
``ProcessPowerThrottling`` and a state mask of zero turns that off for the calling process.

Stdlib only (``ctypes``). On any other system, or when the call fails, nothing happens and the functions return a
negative answer (False, None): the work runs as before.
"""
from __future__ import annotations

import sys

_PROCESS_POWER_THROTTLING = 4                 # PROCESS_INFORMATION_CLASS ProcessPowerThrottling
_CURRENT_VERSION = 1                          # PROCESS_POWER_THROTTLING_CURRENT_VERSION
_EXECUTION_SPEED = 1                          # PROCESS_POWER_THROTTLING_EXECUTION_SPEED


def _state_type():
    import ctypes
    from ctypes import wintypes

    class ProcessPowerThrottlingState(ctypes.Structure):   # 12 bytes: three ULONGs
        _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG), ("StateMask", wintypes.ULONG)]

    return ctypes, ProcessPowerThrottlingState


def _set_execution_speed_throttling(throttled: bool) -> bool:
    """Control the execution-speed throttling of the calling process (this process decides; off when ``throttled`` is False)."""
    ctypes, state_type = _state_type()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.SetProcessInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong]
    kernel32.SetProcessInformation.restype = ctypes.c_int
    state = state_type(_CURRENT_VERSION, _EXECUTION_SPEED, _EXECUTION_SPEED if throttled else 0)
    ok = kernel32.SetProcessInformation(kernel32.GetCurrentProcess(), _PROCESS_POWER_THROTTLING, ctypes.byref(state),
                                        ctypes.sizeof(state))
    return bool(ok)


def opt_out_of_power_throttling() -> bool:
    """Turn the execution-speed throttling of this process off. True when the system accepted it; False on any other system
    or when the call fails. Never raises, and is safe to call again (a pool initializer, and the calling process)."""
    if sys.platform != "win32":
        return False
    try:
        return _set_execution_speed_throttling(False)
    except Exception:   # noqa: BLE001 - an old Windows without the API, a locked-down process: the work runs as before
        return False


def read_power_throttling() -> tuple[int, int] | None:
    """``(ControlMask, StateMask)`` of this process's power throttling as the system reports it, or None when it cannot be read
    (another system, or no API). After ``opt_out_of_power_throttling`` it is ``(1, 0)``."""
    if sys.platform != "win32":
        return None
    try:
        ctypes, state_type = _state_type()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.GetProcessInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong]
        kernel32.GetProcessInformation.restype = ctypes.c_int
        state = state_type(_CURRENT_VERSION, 0, 0)   # the call refuses (error 87) a state whose Version is not set
        if not kernel32.GetProcessInformation(kernel32.GetCurrentProcess(), _PROCESS_POWER_THROTTLING, ctypes.byref(state),
                                              ctypes.sizeof(state)):
            return None
        return int(state.ControlMask), int(state.StateMask)
    except Exception:   # noqa: BLE001
        return None
