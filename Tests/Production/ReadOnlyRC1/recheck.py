import sys,os,hashlib,subprocess,json,zipfile
from pathlib import Path
api="repos/dcajacob/orbiter-cross-platform/actions"
run=44965024779
source="f6c66ea75fb837eb05cd61fc847fc3ec3ca37420"
out=Path("out").resolve()
out.mkdir(exist_ok=True)
def call(*args): subprocess.run(args,check=True)
def sha(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
items=json.loads(subprocess.check_output(["gh","api",f"{api}/runs/{run}/artifacts"]))["artifacts"]
record,=[r for r in items if r["name"]=="User-profile-distribution-"+os.environ["TEST_RUNNER"]]
assert record["workflow_run"]["head_sha"]==source and not record["expired"]
with (out/"consumer.zip").open("wb") as f: subprocess.run(["gh","api",api+"/artifacts/"+str(record["id"])+"/zip"],stdout=f,check=True)
assert "sha256:"+sha(out/"consumer.zip")==record["digest"]
dest=out/"consumer"
with zipfile.ZipFile(out/"consumer.zip") as z:z.extractall(dest)
for line in (dest/"SHA256SUMS").read_text().splitlines():
    digest,name=line.split("  ");assert Path(name).name==name and sha(dest/name)==digest
installer,=dest.glob("*.pyz");package,=dest.glob("*.zip" if os.name=="nt" else "*.tar.gz")
if os.name=="nt":
    # Keep the verified runtime bytes; replace only the installer program.
    import shutil
    fixed=out/"fixed-consumer"
    fixed.mkdir()
    with zipfile.ZipFile(installer) as old,zipfile.ZipFile(fixed/installer.name,"w") as new:
        for info in old.infolist():
            data=Path("Utils/StockDataInstaller/installer.py").read_bytes() if info.filename=="installer.py" else old.read(info)
            new.writestr(info,data)
    installer=fixed/installer.name
    newpackage=fixed/package.name
    os.link(package,newpackage)
    package=newpackage
    (fixed/"SHA256SUMS").write_text(f"{sha(package)}  {package.name}\n{sha(installer)}  {installer.name}\n")
install=Path(os.environ["RC1_INSTALL"])
call(sys.executable,installer,install,"--cache",out/"cache","--package",package)
call(sys.executable,installer,install,"--verify-only")
if os.name=="nt":
    call(sys.executable,"Tests/Production/stage_mesa.py","stage","--cache",out/"mesa-cache","--destination",out/"mesa")
    sys.path.insert(0,str(Path("Tests/Production/Client").resolve()))
    from run_client import mesa_files
    mesa_files(out/"mesa",install/"runtime")
print("Exact package",package.name,sha(package),"from",record["id"])
