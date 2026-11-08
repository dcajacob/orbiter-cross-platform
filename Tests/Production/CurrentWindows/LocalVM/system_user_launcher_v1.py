"""Dispatch the current qualification worker under the existing VM user token."""
import json
from pathlib import Path
import sys
import traceback
from win_local_process_v1 import *

request = Path(sys.argv[1])
config = json.loads(request.read_text())
token = W.HANDLE()
environment = C.c_void_p()
process = None
record = dict(status='starting-normal-user-bootstrap', context=context(), request_sha256=sha(request),
              launcher_sha256=sha(__file__), no_desktop_switch=True)
try:
    session = int(k.WTSGetActiveConsoleSessionId())
    assert session == config['active_session']
    assert wts.WTSQueryUserToken(session, C.byref(token)), C.WinError(C.get_last_error())
    assert ue.CreateEnvironmentBlock(C.byref(environment), token, False), C.WinError(C.get_last_error())
    for field in ('worker', 'bootstrap'):
        assert sha(config[field + '_script']) == config[field + '_sha256']
    process = spawn([sys.executable, '-B', config['bootstrap_script'], str(request)],
                    'winsta0\\default', config['source'], token, environment)
    record.update(status='launched-normal-user-bootstrap', active_session=session, actual_bootstrap_pid=process.dwProcessId)
except BaseException as error:
    record.update(status='failed', error=str(error), traceback=traceback.format_exc())
    raise
finally:
    if process:
        k.CloseHandle(process.hThread)
        k.CloseHandle(process.hProcess)
    if environment:
        ue.DestroyEnvironmentBlock(environment)
    if token:
        k.CloseHandle(token)
    (request.parent / (config['name'] + '-system-launch.json')).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record), flush=True)
