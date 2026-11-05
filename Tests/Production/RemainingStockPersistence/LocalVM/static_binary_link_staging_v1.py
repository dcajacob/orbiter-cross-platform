"""Keep exact C: immutable DLL/EXE staging bytes while avoiding duplicate storage."""
import hashlib,os,shutil,threading
from pathlib import Path
class BinaryLinks:
 def __init__(self,inputs,output):
  self.original=shutil.copy2;self.inputs={os.path.normcase(str(Path(p).resolve())):(Path(p),v) for p,v in inputs.items() if Path(p).suffix.lower() in ('.dll','.exe')};self.output=Path(output).resolve();self.lock=threading.Lock();self.links=[];self.fallback=[]
  assert all(self.sha(p)==v for p,v in self.inputs.values())
 @staticmethod
 def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
 def copy2(self,source,destination,*,follow_symlinks=True):
  incoming=Path(source).resolve();target=Path(destination);key=os.path.normcase(str(incoming));allowed=key in self.inputs and self.output in target.resolve().parents and incoming.drive.casefold()==target.resolve().drive.casefold() and not target.exists() and follow_symlinks
  if allowed:
   try:os.link(incoming,target)
   except OSError as error:
    with self.lock:self.fallback.append(dict(source=str(incoming),target=str(target),error_type=type(error).__name__,winerror=getattr(error,'winerror',None)))
   else:
    assert target.stat().st_ino==incoming.stat().st_ino
    with self.lock:self.links.append(dict(source=str(incoming),target=str(target),sha256=self.inputs[key][1],file_id=target.stat().st_ino))
    return destination
  return self.original(source,destination,follow_symlinks=follow_symlinks)
 def install(self):assert shutil.copy2 is self.original;shutil.copy2=self.copy2
 def close(self):
  shutil.copy2=self.original
  assert all(self.sha(p)==v for p,v in self.inputs.values()),'Immutable input binary changed'
 def controls(self,provider):
  folder=self.output/'local-staging-controls';assert not folder.exists();folder.mkdir(parents=True)
  source=Path(provider)/'opengl32.dll';assert os.path.normcase(str(source.resolve())) in self.inputs
  a=folder/'ordinary-copy.dll';b=folder/'cache-link.dll';self.original(source,a);self.copy2(source,b)
  assert self.sha(a)==self.sha(b)==self.sha(source) and a.stat().st_ino!=source.stat().st_ino and b.stat().st_ino==source.stat().st_ino
  return dict(status='passed-real-NTFS-copy-and-hardlink-byte-equivalence',ordinary_copy_file_id=a.stat().st_ino,hardlink_file_id=b.stat().st_ino,source_file_id=source.stat().st_ino,sha256=self.sha(source))
