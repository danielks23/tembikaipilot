import logging
import os
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

LOG_DIR = "/data/media/0/realdata/tmux"
PARAM_ENABLED = "/data/params/d/TmuxLogsEnabled"
PARAM_LEVEL = "/data/params/d/TmuxLogLevel"
HELPER_SCRIPT = os.path.join(LOG_DIR, "tmux_log.sh")
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def rotate_logs():
    total = sum(
        os.path.getsize(os.path.join(LOG_DIR, f))
        for f in os.listdir(LOG_DIR)
        if f.endswith(".log")
    )
    if total > MAX_LOG_SIZE:
        logs = sorted(
            [
                os.path.join(LOG_DIR, f)
                for f in os.listdir(LOG_DIR)
                if f.endswith(".log")
            ]
        )
        for log in logs:
            total -= os.path.getsize(log)
            os.remove(log)
            if total <= MAX_LOG_SIZE:
                break


def get_log_file():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d--%H%M%S")
    return os.path.join(LOG_DIR, f"tmux-{ts}.log")


def read_param(path: str, default: str = "") -> str:
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return default


def get_log_level() -> str:
    return read_param(PARAM_LEVEL, "all")


def write_helper_script(level: str):
    if level == "errors":
        awk_pattern = "/ERROR|error|failed|Failed|CRITICAL|critical/"
    else:
        awk_pattern = ""

    script = f"""#!/bin/bash
while IFS= read -r line; do
  ts=$(date '+%H:%M:%S')
  if [ -z "{awk_pattern}" ] || echo "$line" | grep -qE 'ERROR|error|failed|Failed|CRITICAL|critical'; then
    echo "$ts $line"
  fi
done
"""
    with open(HELPER_SCRIPT, "w") as f:
        f.write(script)
    os.chmod(HELPER_SCRIPT, stat.S_IRWXU)


def get_pipe_command(log_file: str, level: str) -> str:
    write_helper_script(level)
    return f"{HELPER_SCRIPT} >> {log_file}"


def start_logging(level: str = "all"):
    ensure_log_dir()
    rotate_logs()
    log_file = get_log_file()
    cmd = get_pipe_command(log_file, level)
    try:
        subprocess.run(
            ["tmux", "pipe-pane", "-t", "kommu", cmd],
            check=True,
        )
        logging.info("tmux logging started -> %s (level=%s)", log_file, level)
        return log_file
    except subprocess.CalledProcessError as e:
        logging.error("failed to start tmux logging: %s", e)
        return None


def stop_logging():
    try:
        subprocess.run(["tmux", "pipe-pane", "-t", "kommu"], check=True)
        logging.info("tmux logging stopped")
    except subprocess.CalledProcessError as e:
        logging.error("failed to stop tmux logging: %s", e)


def main():
    from openpilot.common.realtime import set_core_affinity
    set_core_affinity([0, 1, 2, 3])

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
        stream=sys.stderr,
    )

    enabled = read_param(PARAM_ENABLED) == "True"
    level = get_log_level()
    logging.info("tmuxledd started, enabled=%s level=%s", enabled, level)

    current_level = level
    if enabled:
        start_logging(level)

    try:
        while True:
            new_enabled = read_param(PARAM_ENABLED) == "True"
            new_level = get_log_level()

            if new_enabled != enabled or new_level != current_level:
                logging.info("tmux config changed: enabled %s->%s, level %s->%s",
                           enabled, new_enabled, current_level, new_level)
                if enabled and not new_enabled:
                    stop_logging()
                elif not enabled and new_enabled:
                    start_logging(new_level)
                elif enabled and new_level != current_level:
                    stop_logging()
                    start_logging(new_level)
                enabled = new_enabled
                current_level = new_level

            time.sleep(2.5)
    except KeyboardInterrupt:
        if enabled:
            stop_logging()


if __name__ == "__main__":
    main()
