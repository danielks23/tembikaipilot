#!/usr/bin/env python3
"""
status_led.py — robust launcher with preemption and debug

- No --epoch requirement on ws2812.py.
- Preempts previous long-running worker (blink/run) via terminate/kill.
- Uses sys.executable to avoid "python" path issues.
- Optional DEBUG prints if env STATUS_LED_DEBUG=1.
"""

import os
import sys
import time
import shlex
import subprocess
from typing import Optional

WS2812_SCRIPT_DEFAULT = "/usr/kommu/ws2812.py"

# Module-level handle to the currently running worker (for preemption)
_current_proc: Optional[subprocess.Popen] = None

COLORS = {
  "WHITE":  "FFFFFF",
  "RED":    "00FF00",
  "GREEN":  "0000FF",
  "BLUE":   "FF0000",
  "CYAN":   "FF0088",
  "ORANGE": "00FF25",
  "YELLOW": "00DD88",
}

def _dbg(msg: str):
    if os.getenv("STATUS_LED_DEBUG") == "1":
        print(f"[status_led] {msg}", file=sys.stderr)

def parse_color(color: str) -> str:
    if not color:
        raise ValueError("color must be provided")
    c = color.strip().lower()
    for name, hexv in COLORS.items():
        if c == name.lower():
            return hexv
    if c.startswith("#"):
        c = c[1:]
    if len(c) == 6 and all(ch in "0123456789abcdef" for ch in c):
        return c
    raise ValueError(f"Invalid color: {color}")

def _preempt_previous():
    global _current_proc
    if _current_proc is None:
        return
    if _current_proc.poll() is None:
        _dbg("Preempting previous ws2812.py (SIGTERM)...")
        try:
            _current_proc.terminate()
        except Exception as e:
            _dbg(f"terminate() error: {e!r}")
        deadline = time.monotonic() + 0.35
        while time.monotonic() < deadline and _current_proc.poll() is None:
            time.sleep(0.01)
        if _current_proc.poll() is None:
            _dbg("Still running, sending SIGKILL...")
            try:
                _current_proc.kill()
            except Exception as e:
                _dbg(f"kill() error: {e!r}")
    _current_proc = None

def set_upload_indicator(
    status: str,
    *,
    brightness: str = "100",
    ws_script: str = WS2812_SCRIPT_DEFAULT,
    fire_and_forget: bool = True,
):
    """Set cluster B (LEDs 3-5) to show upload status independently.
    
    Args:
        status: 'idle' (off), 'uploading' (blue blink), 'success' (green solid), 'failed' (red blink)
    """
    status_map = {
        "idle": (None, "solid", None),           # off
        "uploading": ("BLUE", "blink", "fast"),   # uploading
        "success": ("GREEN", "solid", None),      # success
        "failed": ("RED", "blink", "fast"),       # failed
    }
    
    if status not in status_map:
        return
    
    color, mode, rate = status_map[status]
    
    if color is None:
        # Turn off - set to black
        set_led("000000", None, mode="solid", brightness=brightness, 
                ws_script=ws_script, fire_and_forget=fire_and_forget)
    else:
        # Set only cluster B (pass same color for A to keep it unchanged, ws2812 handles it)
        py = sys.executable or "python3"
        args = [py, ws_script, mode, "--brightness", brightness, "--a-color", "000000", "--b-color", parse_color(color)]
        
        if mode in ("blink", "run"):
            if rate:
                args += ["--rate", rate]
            args += ["--duration", "600"]
        
        _dbg("exec upload: " + " ".join(shlex.quote(x) for x in args))
        
        if fire_and_forget:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(args, check=False)


def set_led(
    a_color: str,
    b_color: Optional[str] = None,
    *,
    mode: str = "solid",           # 'solid' | 'blink' | 'run'
    rate: Optional[str] = None,    # 'fast' | 'slow'
    duration: Optional[str] = None,# only for blink/run; None -> long sentinel
    brightness: str = "100",       # '0'..'100'
    ws_script: str = WS2812_SCRIPT_DEFAULT,
    fire_and_forget: bool = True,
):
    a_hex = parse_color(a_color)
    b_hex = parse_color(b_color) if b_color else a_hex

    if not os.path.exists(ws_script):
        raise FileNotFoundError(f"ws_script not found: {ws_script}")

    # Preempt any ongoing long-running worker
    _preempt_previous()

    py = sys.executable or "python3"
    args = [py, ws_script, mode, "--brightness", brightness, "--a-color", a_hex, "--b-color", b_hex]

    if mode in ("blink", "run"):
        if rate:
            args += ["--rate", rate]
        if duration is None:
            duration = "600"  # long sentinel; next call will preempt
        args += ["--duration", duration]

    # Debug print the exact command
    _dbg("exec: " + " ".join(shlex.quote(x) for x in args))

    if fire_and_forget:
        # Capture stderr to surface script errors in debug mode
        stderr = None if os.getenv("STATUS_LED_DEBUG") != "1" else subprocess.PIPE
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=stderr, text=True)
        if stderr is not None:
            # Read any immediate error without blocking the process lifetime
            try:
                time.sleep(0.02)
                if proc.poll() is not None:
                    err = proc.stderr.read() if proc.stderr else ""
                    if err:
                        _dbg(f"ws2812.py exited early with stderr:\n{err.strip()}")
            except Exception:
                pass
        if mode in ("blink", "run"):
            global _current_proc
            _current_proc = proc
        return None
    else:
        # Blocking call; show stderr to caller for troubleshooting
        return subprocess.run(args, check=False)

