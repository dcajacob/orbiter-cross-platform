"""Keep a new private desktop alive until the exact current runtime worker exits."""
import json
from pathlib import Path
import sys
import traceback
from win_local_process_v1 import *

request = Path(sys.argv[1])
config = json.loads(request.read_text())
record = dict(status='starting-private-desktop', context=context(), request_sha256=sha(request),
              bootstrap_sha256=sha(__file__), no_desktop_switch=True)
desktop = None
process = None
try:
    assert record['context']['session'] == config['active_session']
    assert sha(__file__) == config['bootstrap_sha256'] and sha(config['worker_script']) == config['worker_sha256']
    desktop = u.CreateDesktopW(config['desktop'], None, None, 0, 0x10000000, None)
    assert desktop, C.WinError(C.get_last_error())
    process = spawn([sys.executable, '-B', config['worker_script'], str(request)], 'winsta0\\' + config['desktop'], config['source'])
    record.update(status='actual-private-worker-started', actual_worker_pid=process.dwProcessId, desktop=config['desktop'])
    (request.parent / (config['name'] + '-bootstrap-started.json')).write_text(json.dumps(record, indent=2) + '\n')
    while k.WaitForSingleObject(process.hProcess, 1000) == 258:
        pass
    code = W.DWORD()
    assert k.GetExitCodeProcess(process.hProcess, C.byref(code))
    record.update(status='actual-private-worker-finished', actual_worker_exitcode=code.value)
    assert code.value == 0, 'Current runtime worker failed'
except BaseException as error:
    record.update(status='failed', error=str(error), traceback=traceback.format_exc())
    raise
finally:
    if process:
        k.CloseHandle(process.hThread)
        k.CloseHandle(process.hProcess)
    if desktop:
        record['private_desktop_closed'] = bool(u.CloseDesktop(desktop))
    (request.parent / (config['name'] + '-bootstrap-result.json')).write_text(json.dumps(record, indent=2) + '\n')
