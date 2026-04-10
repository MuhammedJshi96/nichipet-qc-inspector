import atexit
import os
import sys
import subprocess
from pathlib import Path

import webview

from desktop_utils import find_free_port, wait_for_server, kill_process_tree

APP_TITLE = "Nichipet QC Inspector"
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 980

def get_project_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent

def get_python_executable():
    if getattr(sys, "frozen", False):
        return sys.executable
    return sys.executable

def launch_streamlit():
    project_root = get_project_root()
    app_path = project_root / "app.py"
    if not app_path.exists():
        raise FileNotFoundError(f"Could not find app.py at {app_path}")

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    cmd = [
        get_python_executable(),
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]

    creationflags = 0
    kwargs = {}
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(
        cmd,
        cwd=str(project_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        **kwargs,
    )

    atexit.register(kill_process_tree, proc)

    if not wait_for_server(url, timeout=60):
        kill_process_tree(proc)
        raise RuntimeError("Streamlit server did not start in time.")

    return proc, url

def main():
    proc, url = launch_streamlit()

    window = webview.create_window(
        APP_TITLE,
        url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(1100, 760),
        text_select=True,
    )

    try:
        webview.start(debug=False)
    finally:
        kill_process_tree(proc)

if __name__ == "__main__":
    main()