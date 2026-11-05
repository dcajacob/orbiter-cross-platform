"""Private, version-pinned Weston instance; never operates the desktop compositor."""
import json
import os
from pathlib import Path
import socket
import subprocess
import shutil
import tempfile
import time


class Compositor:
    def __init__(self, dependencies, output, scale=1, renderer='pixman', repeat_rate=None):
        self.dependencies = Path(dependencies).resolve()
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        # Unix-domain socket paths are limited to 107 bytes on this platform.
        # A fresh 0700 directory also isolates the fixture from every session.
        runtime = Path(tempfile.mkdtemp(prefix='orbiter-wl-', dir='/tmp'))
        self.runtime = runtime
        (self.output/'runtime.json').write_text(json.dumps(dict(path=str(runtime),
            mode=oct(runtime.stat().st_mode & 0o777), uid=runtime.stat().st_uid))+'\n')
        prefix = self.dependencies/'root'
        lib = prefix/'usr/lib/x86_64-linux-gnu'
        modules = {p.name: str(p) for folder in (lib/'libweston-14', lib/'weston')
                   for p in folder.glob('*.so')}
        modules.update({p.name: str(p) for p in (prefix/'usr/libexec').glob('weston-*')})
        config = self.output/'weston.ini'
        config.write_text('[core]\nidle-time=0\n[shell]\nclient='+
                          str(prefix/'usr/libexec/weston-desktop-shell')+
                          '\npanel-position=none\nlocking=false\nanimation=none\n'
                          'startup-animation=none\nclose-animation=none\n')
        if repeat_rate is not None:
            if not isinstance(repeat_rate, int) or repeat_rate < 0:
                raise ValueError('Private keyboard repeat rate must be a nonnegative integer')
            with config.open('a') as fixture:
                fixture.write('[keyboard]\nrepeat-rate='+str(repeat_rate)+'\nrepeat-delay=400\n')
        self.socket, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.socket.settimeout(15)
        environment = dict(os.environ, XDG_RUNTIME_DIR=str(runtime),
                           WESTON_MODULE_MAP=';'.join(k+'='+v for k, v in modules.items()),
                           WESTON_DATA_DIR=str(prefix/'usr/share/weston'),
                           LD_LIBRARY_PATH=str(lib)+':'+str(lib/'weston'),
                           ORBITER_TEST_CONTROL_FD=str(child.fileno()),
                           ORBITER_TEST_CONTROLLER_PID=str(os.getpid()))
        for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'LD_PRELOAD'):
            environment.pop(name, None)
        argv = [str(prefix/'usr/bin/weston'), '--backend=headless', '--renderer='+renderer,
                '--width=1920', '--height=1080', '--scale='+str(scale),
                '--socket=orbiter-test', '--shell=desktop-shell.so',
                '--modules='+str(self.dependencies/'compositor-input.so'),
                '--config='+str(config), '--log='+str(self.output/'weston.log')]
        (self.output/'invocation.json').write_text(json.dumps(argv, indent=2)+'\n')
        self.trace = (self.output/'control.jsonl').open('w')
        self.log = (self.output/'console.log').open('w')
        self.process = subprocess.Popen(argv, stdout=self.log, stderr=subprocess.STDOUT,
                                        env=environment, pass_fds=(child.fileno(),))
        child.close()
        try:
            self.receive('ready')
        except BaseException:
            self.close()
            raise
        self.environment = dict(os.environ, XDG_RUNTIME_DIR=str(runtime),
                                WAYLAND_DISPLAY='orbiter-test', XDG_SESSION_TYPE='wayland')
        for name in ('DISPLAY', 'LD_PRELOAD'):
            self.environment.pop(name, None)

    def receive(self, command):
        packet = self.socket.recv(4096)
        if not packet:
            raise RuntimeError('Private Weston exited; inspect '+str(self.output/'weston.log'))
        reply = json.loads(packet)
        self.trace.write(json.dumps(dict(monotonic_ns=time.monotonic_ns(), command=command,
                                        reply=reply))+'\n')
        self.trace.flush()
        return reply

    def command(self, command, allow_unmapped=False):
        self.socket.send(command.encode('ascii'))
        reply = self.receive(command)
        if not reply['ok'] and not (allow_unmapped and reply['error']=='owned surface not mapped'):
            raise RuntimeError('Weston command '+command+': '+reply['error'])
        return reply

    def surface(self, pid):
        reply = self.command('surface '+str(pid), allow_unmapped=True)
        return reply if reply['ok'] else None

    def close(self):
        try:
            if self.process.poll() is None:
                try:
                    self.command('quit')
                    self.process.wait(timeout=10)
                except (OSError, RuntimeError, subprocess.TimeoutExpired):
                    self.process.terminate()
                    self.process.wait(timeout=10)
        finally:
            (self.output/'lifecycle.json').write_text(json.dumps(dict(returncode=self.process.returncode))+'\n')
            self.socket.close()
            self.trace.close()
            self.log.close()
            shutil.rmtree(self.runtime)
        if self.process.returncode!=0:
            raise RuntimeError('Private Weston did not shut down normally')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
