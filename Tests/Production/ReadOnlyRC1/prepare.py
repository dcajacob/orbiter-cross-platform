"""Fetch the frozen public package and installer and exercise the SDK as a consumer."""
import hashlib, json, os, platform, subprocess, sys, zipfile
from pathlib import Path

root=Path.cwd()
out=root/"out"
dist=out/"distribution"
dist.mkdir(parents=True)
win=os.name=="nt"
arch="x86_64" if win else platform.machine()
name=("Orbiter-windows-x64-8e576b84.zip" if win else f"Orbiter-macos-{arch}-8e576b84.tar.gz")
locks=Path(__file__).with_name("candidate-packages.json")
info=json.loads(locks.read_text())[name]
def sha(path):
    with path.open("rb") as f: return hashlib.file_digest(f,"sha256").hexdigest()
def require(ok, why):
    if not ok: raise ValueError(why)
def run(*cmd):
    subprocess.run(cmd,check=True)
def py(*args): run(sys.executable,"-B",*args)
api="repos/dcajacob/orbiter-cross-platform/actions/artifacts/"+str(info["artifact"])
record=json.loads(subprocess.check_output(["gh","api",api]))
require(not record["expired"] and record["digest"]==info["artifact_digest"] and record["workflow_run"]["head_sha"]==info["source"], "Unexpected artifact identity")
with (out/"sealed.zip").open("wb") as f:
    subprocess.run(["gh","api",api+"/zip"],stdout=f,check=True)
require("sha256:"+sha(out/"sealed.zip")==info["artifact_digest"], "Artifact download checksum")
pyzname="orbiter-stock-data.pyz" if win else f"orbiter-stock-data-{arch}.pyz"
with zipfile.ZipFile(out/"sealed.zip") as z:
    for p in (name,pyzname): z.extract(p,out)
require(sha(out/name)==info["sha256"] and sha(out/pyzname)==info["installer_sha256"],"Frozen payload checksum")

