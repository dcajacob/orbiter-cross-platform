"""Create a private test desktop in the logged-in user's VM session."""
import json,sys,time,traceback
from pathlib import Path
from win_local_process_v1 import *
request=Path(sys.argv[1]);config=json.loads(request.read_text());name=config['name'];share=Path('O:/');record=dict(status='starting-private-runtime-desktop',context=context(),request_sha256=sha(request),no_desktop_switch=True)
desk=None;pi=None
try:
 assert record['context']['session']==config['active_session'] and sha(config['worker_script'])==config['worker_sha256']
 desk=u.CreateDesktopW(config['desktop'],None,None,0,0x10000000,None);assert desk,C.WinError(C.get_last_error())
 pi=spawn([sys.executable,'-B',config['worker_script'],str(request)],'winsta0\\'+config['desktop'],config['source'])
 record.update(status='actual-private-runtime-worker-started',actual_worker_pid=pi.dwProcessId,desktop=config['desktop']);(share/(name+'-bootstrap-started.json')).write_text(json.dumps(record,indent=2)+'\n')
 while k.WaitForSingleObject(pi.hProcess,1000)==258:pass
 code=W.DWORD();assert k.GetExitCodeProcess(pi.hProcess,C.byref(code));record.update(status='private-runtime-worker-finished',actual_worker_exitcode=code.value)
 assert code.value==0,'Actual local original runtime worker failed'
except BaseException as error:record.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
finally:
 if pi:
  k.CloseHandle(pi.hThread);k.CloseHandle(pi.hProcess)
 if desk:record['private_desktop_closed']=bool(u.CloseDesktop(desk))
 (share/(name+'-bootstrap-result.json')).write_text(json.dumps(record,indent=2)+'\n')
