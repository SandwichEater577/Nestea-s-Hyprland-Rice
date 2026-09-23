#!/usr/bin/env python3
"""Emit Waybar JSON when PipeWire/PulseAudio changes, without polling."""
import signal
import os
import subprocess
import sys
import time
import desktop

def stop(*_):raise SystemExit(0)
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
def emit(*_):
    desktop.audio('status');sys.stdout.flush()
signal.signal(signal.SIGUSR1,emit)
(desktop.STATE/'audio-watch.pid').write_text(str(os.getpid()))
while True:
    proc=None
    try:
        proc=subprocess.Popen(['pactl','subscribe'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)
        desktop.audio('status');sys.stdout.flush()
        for line in proc.stdout:
            if ' on sink ' in line or ' on server ' in line:
                desktop.audio('status');sys.stdout.flush()
    except (OSError,subprocess.SubprocessError,ValueError):pass
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
    time.sleep(2)
