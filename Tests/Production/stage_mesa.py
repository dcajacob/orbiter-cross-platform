#!/usr/bin/env python3
"""Use the native Windows archive reader without changing the frozen Mesa stager."""
import json,os,shutil,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from mesa_runtime import main,digest,require
if __name__=='__main__':
    if sys.platform=='win32':
        tool=Path(os.environ['SystemRoot'])/'System32/tar.exe'
        require(tool.is_file(),'Native Windows archive reader is missing')
        os.environ['PATH']=str(tool.parent)+os.pathsep+os.environ.get('PATH','')
        selected=Path(shutil.which('tar') or '').resolve()
        require(selected==tool.resolve(),'Native Windows archive reader was not selected')
        version=subprocess.check_output([str(tool),'--version'],text=True).strip()
        print(json.dumps(dict(archive_tool=str(selected),sha256=digest(selected),version=version)),flush=True)
    main()
