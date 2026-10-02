#!/usr/bin/env python3
"""Timed exploratory RF presence test. Run on the Pi with rtl-sdr installed."""
import datetime as dt
import json
from pathlib import Path
import random
import signal
import subprocess
import time

folder = Path.home() / ('presence-control-test-' + dt.datetime.now().strftime('%Y%m%d-%H%M%S'))
folder.mkdir()
events = []
proc = None
failed = False
# Balance conditions within each half to limit confounding by slow drift.
order = []
for _ in range(2):
    block = ['person', 'person', 'control', 'control']
    random.SystemRandom().shuffle(block)
    order.extend(block)
completed = False

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
    for trial, condition in enumerate(order, 1):
        if condition == 'person':
            announce(f'Round {trial} of eight. Enter now. Stand on the marked spot.')
        else:
            announce(f'Round {trial} of eight. Stay outside the room. This is a control round.')
        phase(f'trial_{trial}_{condition}_entry_transition', 10)
        announce('Hold still where you are. Measuring now.')
        phase(f'trial_{trial}_{condition}', 15)
        if condition == 'person':
            announce('Leave the room now.')
        else:
            announce('Keep staying outside the room.')
        phase(f'trial_{trial}_{condition}_exit_transition', 10)
        phase(f'trial_{trial}_empty', 20)
    completed = True
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
    (folder / 'phases.json').write_text(json.dumps({'protocol': 'balanced-randomized-presence-v1', 'completed': completed, 'trial_order': order, 'analysis_plan': {'band_hz': [89150000, 89450000], 'boundary_trim_seconds': 2, 'metric': 'Convert bins to linear power, average within band, then convert to dB. For each trial compare the measurement mean with the mean of its preceding and following empty periods. Compare person and control trial effects; trials, not per-second rows, are replicates.'}, 'frequency_hz': [88000000, 90500000], 'gain_db': 20.7, 'note': 'Local Pi timestamps; omit measurements overlapping transition boundaries.', 'phases': events}, indent=2))
    print('RESULT:' + str(folder), flush=True)

if failed:
    raise SystemExit(1)
