"""Launch the local runtime under the VM's already logged-in user token."""
import json,sys
from pathlib import Path
from win_local_process_v1 import *
def main(path):
 request=Path(path);config=json.loads(request.read_text());name=config['name'];token=W.HANDLE();env=C.c_void_p();pi=None;record=dict(status='starting-normal-user-bootstrap',request_sha256=sha(request),no_desktop_switch=True)
 try:
  session=int(k.WTSGetActiveConsoleSessionId());assert session==config['active_session'] and wts.WTSQueryUserToken(session,C.byref(token)),C.WinError(C.get_last_error())
  assert ue.CreateEnvironmentBlock(C.byref(env),token,False),C.WinError(C.get_last_error())
  assert sha(config['bootstrap_script'])==config['bootstrap_sha256'] and sha(config['worker_script'])==config['worker_sha256']
  pi=spawn([sys.executable,'-B',config['bootstrap_script'],str(request)],'winsta0\\default',config['source'],token,env)
  record.update(status='launched-normal-user-local-runtime-bootstrap',active_session=session,actual_bootstrap_pid=pi.dwProcessId)
 finally:
  if pi:k.CloseHandle(pi.hThread);k.CloseHandle(pi.hProcess)
  if env:ue.DestroyEnvironmentBlock(env)
  if token:k.CloseHandle(token)
  Path('O:/'+name+'-system-launch.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(record),flush=True)
