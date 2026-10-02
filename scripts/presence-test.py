#!/usr/bin/env python3
"""Timed exploratory RF presence test. Run on the Pi with rtl-sdr installed."""
import datetime as dt
import json
from pathlib import Path
import signal
import subprocess
import time

folder = Path.home() / ('presence-test-' + dt.datetime.now().strftime('%Y%m%d-%H%M%S'))
folder.mkdir()
events = []
proc = None
failed = False

def announce(text):
    print('SAY:' + text, flush=True)

def phase(name, seconds):
    start = dt.datetime.now().isoformat()
    print(f'PHASE: {name} ({seconds} seconds)', flush=True)
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError('SDR stopped unexpectedly. See receiver.log in ' + str(folder))
        time.sleep(min(0.2, max(0, end - time.monotonic())))
    events.append(dict(phase=name, start=start, end=dt.datetime.now().isoformat()))

try:
    announce('Sound check. Leave the room now. Recording begins in twenty seconds.')
    phase('departure', 20)
    log = (folder / 'receiver.log').open('w')
    proc = subprocess.Popen(['rtl_power', '-f', '88M:90.5M:25k', '-g', '20.7', '-i', '1', str(folder / 'spectrum.csv')], stdout=log, stderr=log)
    phase('receiver_warmup', 10)
    announce('Stay outside. Measuring the empty room.')
    phase('empty_control_a', 20)
    phase('empty_control_b', 20)
    for trial in range(1, 4):
        announce(f'Enter now. Trial {trial}. Stand on the marked spot without touching the antenna.')
        phase(f'trial_{trial}_enter_transition', 10)
        announce('Hold still.')
        phase(f'trial_{trial}_person', 15)
        announce('Leave the room now.')
        phase(f'trial_{trial}_leave_transition', 10)
        phase(f'trial_{trial}_empty', 20)
    announce('Test complete. You can return.')
except KeyboardInterrupt:
    failed = True
    print('Test cancelled.', flush=True)
except Exception as exc:
    failed = True
    print('ERROR: ' + str(exc), flush=True)
    announce('Test stopped. Please check Terminal.')
finally:
    if proc is not None and proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=5)
    (folder / 'phases.json').write_text(json.dumps({'frequency_hz': [88000000, 90500000], 'gain_db': 20.7, 'note': 'Local Pi timestamps; omit measurements overlapping transition boundaries.', 'phases': events}, indent=2))
    print('RESULT:' + str(folder), flush=True)

if failed:
    raise SystemExit(1)
