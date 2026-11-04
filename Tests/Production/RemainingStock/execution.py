"""Bound independent scene processes while recording every outcome on one thread."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
from pathlib import Path
import subprocess
import time


def worker_count(value):
    count = int(value)
    if count not in (1, 2, 3, 4):
        raise ValueError('Scene workers must be between 1 and 4')
    return count


def collect(cases, workers, observe, record):
    if type(workers) is not int or workers not in (1, 2, 3, 4):
        raise ValueError('Scene workers must be between 1 and 4')
    cases = list(cases)
    identities = [case['id'] for case in cases]
    if not cases or len(identities) != len(set(identities)):
        raise ValueError('Nonempty unique scene identities required')
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(observe, case): case for case in cases}
        for future in as_completed(futures):
            case = futures[future]
            try:
                result = future.result()
            except Exception as error:
                record(case, None, error)
            else:
                record(case, result, None)


def run_process(argv, directory, timeout_seconds=240):
    if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 900:
        raise ValueError('Process wall-time limit must be in (0, 900] seconds')
    directory = Path(directory)
    started = time.monotonic_ns()
    process = None
    timed_out = False
    try:
        with (directory/'console.txt').open('w') as console:
            process = subprocess.Popen(argv, cwd=directory, stdout=console, stderr=subprocess.STDOUT)
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                process.wait()
                raise
            except BaseException:
                process.kill()
                process.wait()
                raise
        return process
    finally:
        elapsed = time.monotonic_ns() - started
        if process is not None and process.returncode is not None:
            (directory/'process-result.json').write_text(json.dumps(dict(returncode=process.returncode))+'\n')
        (directory/'process-timing.json').write_text(json.dumps(dict(
            elapsed_wall_ns=elapsed, timeout_seconds=timeout_seconds, timed_out=timed_out,
            actual_pid=process.pid if process is not None else None,
            actual_returncode=process.returncode if process is not None else None), indent=2)+'\n')
