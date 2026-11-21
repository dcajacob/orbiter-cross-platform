"""Run the installed GUI as the hosted console user with standard membership."""
import os
import pwd
import subprocess
import sys
import time
account=pwd.getpwnam(os.environ["SUDO_USER"])
name=account.pw_name
def edit(operation):
    subprocess.run(["/usr/sbin/dseditgroup","-o","edit",operation,name,"-t","user","admin"],check=True)
def demote():
    os.initgroups(name,account.pw_gid)
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)
original=subprocess.check_output(["/usr/bin/id","-Gn",name],text=True).split()
try:
    if "admin" in original:
        edit("-d")
    for _ in range(20):
        groups=subprocess.check_output(["/usr/bin/id","-Gn",name],text=True).split()
        if "admin" not in groups: break
        time.sleep(.5)
    if "admin" in groups: raise RuntimeError("Console user is still an administrator")
    print("Effective account",name,"directory groups",groups,flush=True)
    env=dict(os.environ,HOME=account.pw_dir,USER=name,LOGNAME=name)
    proc=subprocess.run([sys.executable,*sys.argv[1:]],env=env,preexec_fn=demote)
    sys.exit(proc.returncode)
finally:
    if "admin" in original:
        edit("-a")
