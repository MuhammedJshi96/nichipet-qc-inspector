import socket
import time
import urllib.request
import subprocess
import os
import signal

def find_free_port(start=8501, end=8599):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free port found between 8501 and 8599.")

def wait_for_server(url: str, timeout: int = 60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def kill_process_tree(proc: subprocess.Popen):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)])
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            proc.terminate()