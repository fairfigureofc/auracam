"""Exercise a whole capture without hardware or real waiting."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

class Clock:
    t = 0
    def monotonic(self): return self.t
    def sleep(self, seconds): self.t += seconds

class Receiver:
    def poll(self): return None
    def send_signal(self, signal): pass
    def wait(self, timeout): pass

class ProtocolTest(unittest.TestCase):
    def test_complete_randomized_capture(self):
        clock = Clock()
        with tempfile.TemporaryDirectory() as td:
            with patch('pathlib.Path.home', return_value=Path(td)), patch('time.monotonic', clock.monotonic), patch('time.sleep', clock.sleep), patch('subprocess.Popen', return_value=Receiver()), contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(ROOT / 'scripts/presence-control-test.py'), run_name='__main__')
            result = json.loads(next(Path(td).glob('*/phases.json')).read_text())
            self.assertTrue(result['completed'])
            self.assertEqual(round(clock.t), 510)
            for block in [result['trial_order'][:4], result['trial_order'][4:]]:
                self.assertEqual(block.count('person'), 2)
                self.assertEqual(block.count('control'), 2)
            self.assertEqual(len(result['phases']), 36)

if __name__ == '__main__': unittest.main()
