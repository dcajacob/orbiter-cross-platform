import os,pwd,sys
account=pwd.getpwnam(os.environ['SUDO_USER'])
os.setgroups([20])
os.setgid(20)
os.setuid(account.pw_uid)
os.environ.update(HOME=account.pw_dir,USER=account.pw_name,LOGNAME=account.pw_name)
os.execv(sys.executable,[sys.executable,*sys.argv[1:]])
