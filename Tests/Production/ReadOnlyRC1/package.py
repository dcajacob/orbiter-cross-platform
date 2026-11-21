"""Repack only the rebuilt components, preserving the RC1 data inputs and installer."""
from pathlib import Path
import os,sys,shutil,subprocess,json,hashlib,tarfile,zipfile
out=Path("out").resolve()
win=os.name=="nt"
old=next(out.glob("Orbiter-*-8e576b84.*"))
archive=out/"payload"
archive.mkdir()
def sha(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def run(*args,**kw):subprocess.run(args,check=True,**kw)
if win:
    with zipfile.ZipFile(old) as z:z.extractall(archive)
else:
    with tarfile.open(old) as z:z.extractall(archive,filter="data")
manifest=json.loads((archive/"runtime.json").read_text())
if win:
    engines=[p for p in (out/"app").rglob("Orbiter.exe") if p.is_file()]
    assert len(engines)==1,engines
    shutil.copy2(engines[0],archive/"Orbiter.exe")
    shutil.copy2(out/"launcher/orbiter-launchpad.exe",archive/"orbiter-launchpad.exe")
else:
    app=out/"launcher/orbiter-launchpad.app"
    qt=next((out/"qt").rglob("macdeployqt"))
    run(qt,app,"-no-strip")
    run("codesign","--force","--deep","--sign","-",app)
    run("codesign","--verify","--deep","--strict",app)
    shutil.rmtree(archive/app.name)
    shutil.copytree(app,archive/app.name,symlinks=True)
source=os.environ["GITHUB_SHA"]
manifest["component_base_source"]=manifest["source"]
manifest["source"]=source
manifest["files"]={p.relative_to(archive).as_posix():sha(p) for p in archive.rglob("*") if p.is_file() and p!=archive/"runtime.json"}
(archive/"runtime.json").write_text(json.dumps(manifest,indent=2)+"\n")
dist=out/"fixed";dist.mkdir()
new=dist/old.name.replace("8e576b84","user-profile-"+source[:8])
if win:
    with zipfile.ZipFile(new,"w",zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for p in archive.rglob("*"):
            if p.is_file():z.write(p,p.relative_to(archive))
else:
    run("tar","-czf",new,"-C",archive,".")
oldpy=next(out.glob("orbiter-stock-data*.pyz"))
installer=dist/oldpy.name
with zipfile.ZipFile(oldpy) as src,zipfile.ZipFile(installer,"w") as dst:
    for member in src.infolist():
        data=src.read(member)
        if member.filename=="packages.json":
            lock=json.loads(data)[old.name];lock.update(sha256=sha(new),source=source)
            data=json.dumps({new.name:lock},indent=2).encode()
        dst.writestr(member,data)
(dist/"SHA256SUMS").write_text(f"{sha(new)}  {new.name}\n{sha(installer)}  {installer.name}\n")
install=Path(os.environ["RC1_INSTALL"])
run(sys.executable,installer,install,"--cache",out/"cache","--package",new)
run(sys.executable,installer,install,"--verify-only")
if win:
    run(sys.executable,"Tests/Production/stage_mesa.py","stage","--cache",out/"mesa-cache","--destination",out/"mesa")
    sys.path.insert(0,str(Path("Tests/Production/Client").resolve()))
    from run_client import mesa_files
    mesa_files(out/"mesa",install/"runtime")
