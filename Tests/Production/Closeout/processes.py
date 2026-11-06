"""Own collector processes by PID and Linux start token, including new-session children."""
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

from contracts import require


def identity(pid):
    try:
        text = (Path('/proc') / str(pid) / 'stat').read_text()
        fields = text[text.rindex(')') + 2:].split()
        argv = (Path('/proc') / str(pid) / 'cmdline').read_bytes().split(b'\0')
        return dict(pid=pid, parent=int(fields[1]), start_ticks=int(fields[19]), state=fields[0],
                    argv=[s.decode(errors='replace') for s in argv if s])
    except (OSError, ValueError):
        return None


def same_process(record):
    actual = identity(record['pid'])
    return actual is not None and actual['start_ticks'] == record['start_ticks']


class OwnedProcess:
    def __init__(self, argv, **kwargs):
        self.lock = threading.RLock()
        self.process = subprocess.Popen(argv, start_new_session=True, **kwargs)
        self.started_ns = time.time_ns()
        root = identity(self.process.pid)
        require(root is not None, 'Collector disappeared before its identity was recorded')
        self.known = {self.process.pid: root}
        self.cancelled = False

    def discover(self):
        with self.lock:
            candidates = []
            for entry in Path('/proc').iterdir():
                if entry.name.isdigit():
                    record = identity(int(entry.name))
                    if record:
                        candidates.append(record)
            changed = True
            while changed:
                changed = False
                for record in candidates:
                    parent = self.known.get(record['parent'])
                    if record['pid'] not in self.known and parent and same_process(parent):
                        self.known[record['pid']] = record
                        changed = True
            return list(self.known.values())

    def cancel(self, grace=5):
        with self.lock:
            # A completed collector remains available for audit; cancellation is
            # a separate state, never an alias for successful completion.
            records = self.discover()
            live_children = any((current := identity(r['pid'])) and
                                current['start_ticks'] == r['start_ticks'] and current['state'] != 'Z'
                                for r in records if r['pid'] != self.process.pid)
            if self.process.poll() is not None and not live_children:
                return self.receipt()
            self.cancelled = True
            for record in reversed(records):
                if same_process(record):
                    try:
                        os.kill(record['pid'], signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            deadline = time.monotonic() + grace
            while time.monotonic() < deadline:
                self.process.poll()
                if not any((current := identity(r['pid'])) and current['start_ticks'] == r['start_ticks'] and
                           current['state'] != 'Z' for r in records):
                    break
                time.sleep(.02)
            for record in reversed(records):
                if same_process(record):
                    try:
                        os.kill(record['pid'], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            self.process.wait()
            return self.receipt()

    def receipt(self):
        with self.lock:
            code = self.process.poll()
            return dict(actual_collector_pid=self.process.pid, actual_returncode=code,
                        collector_started_wall_ns=self.started_ns, cancelled=self.cancelled,
                        terminal=code is not None, owned_process_identities=list(self.known.values()),
                        # Child exit codes come from the collector's simulator
                        # receipts, never from /proc disappearance.
                        simulator_receipts_required=True)
