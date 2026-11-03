#!/usr/bin/env python3
"""Check actual numerical bindings against frozen Windows and independent MPFR."""
import argparse,csv,ctypes as C,errno,gzip,hashlib,json,math,random,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent
FUNCTIONS=('sin','cos','asin','atan2','exp')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bits(x):return struct.unpack('>Q',struct.pack('>d',x))[0]
def ordered(x):
    n=bits(x);return (~n)&((1<<64)-1) if n>>63 else n|(1<<63)
def require(value,message):
    if not value:raise ValueError(message)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--probe',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    lib=C.CDLL(str(a.probe.resolve()))
    for name in ('probe_value','oracle_value'):
        f=getattr(lib,name);f.argtypes=[C.c_int,C.c_double,C.c_double]+([C.c_uint] if name=='oracle_value' else []);f.restype=C.c_double
    lib.probe_bits.argtypes=[C.c_int,C.c_uint64,C.c_uint64];lib.probe_bits.restype=C.c_double
    for name in ('probe_profile','oracle_version','oracle_module'):getattr(lib,name).restype=C.c_char_p
    profile=lib.probe_profile().decode();oracle=Path(lib.oracle_module().decode()).resolve()
    # The original stored SurfParam and CRT asin use this exact input at tick
    # 34 in the atmospheric DG. Source run 41560881876, same Windows host.
    lib.probe_latitude.argtypes=[C.c_double];lib.probe_latitude.restype=C.c_double
    latitude=lib.probe_latitude(float.fromhex('0x1.e92199644661ep-2'))
    expected_latitude='0x1.fdf30f8d54924p-2' if lib.probe_release_latitude() or profile.endswith('sse2') else '0x1.fdf30f8d54923p-2'
    require(latitude.hex()==expected_latitude,'Equatorial latitude differs from its original CRT profile')
    rng=random.Random(0x4f524249544552);samples=[]
    values=[0.,-0.,math.ulp(0.),-math.ulp(0.),1.,-1.,float.fromhex('0x1.fffffffffffffp+1023')]
    for x in (.0001,.6,math.pi/4,math.pi/2,math.pi,2*math.pi,500000.,20000000.,1e100,1e308):
        for sign in (-1,1):
            z=x*sign;values.extend((z,math.nextafter(z,-math.inf),math.nextafter(z,math.inf)))
    for i in range(1500):
        x=struct.unpack('>d',rng.getrandbits(64).to_bytes(8,'big'))[0]
        if math.isfinite(x):values.append(x)
    for f in (0,1):samples.extend((f,x,0.) for x in values)
    samples.extend((2,x,0.) for x in (0.,-0.,1.,-1.,math.nextafter(1.,0.),math.nextafter(-1.,0.),math.ulp(0.),-math.ulp(0.)))
    samples.extend((2,rng.uniform(-1,1),0.) for i in range(1500))
    samples.extend((3,x,y) for x in (0.,-0.,1.,-1.,1e308,-1e308,math.ulp(0.)) for y in (0.,-0.,1.,-1.,1e308,-1e308,math.ulp(0.)))
    samples.extend((3,rng.choice(values),rng.choice(values)) for i in range(1500))
    samples.extend((4,rng.uniform(-744.,709.),0.) for i in range(1500))
    samples.extend((4,x,0.) for x in (0.,-0.,-745.,-744.,-709.,709.,float.fromhex('-0x1.1f77269225794p-1')))
    expected=[]
    for f,x,y in samples:
        low=lib.oracle_value(f,x,y,256);high=lib.oracle_value(f,x,y,512)
        require(bits(low)==bits(high),'MPFR precisions disagree on the rounded oracle')
        expected.append(high)
    provenance=json.loads((HERE/'Reference/provenance.json').read_text());reports=[]
    require(provenance['automatic_refresh'] is False and provenance['run_id']==41382988661 and
            provenance['application_source']=='391919027ac3e4a4d42f145373c788fc859c32cd','Wrong original Windows primitive oracle')
    # Exercise production automatic dispatch first, then the other CPU path.
    auto=1 if profile.endswith('fma3') else 0
    modes=[('automatic',auto,-1)]+([('sse2',0,0)] if auto else ([('fma3',1,1)] if lib.probe_fma_available() else []))
    for label,mode,select in modes:
        if select>=0:lib.probe_mode(select)
        maxima={name:0 for name in FUNCTIONS}
        for (f,x,y),target in zip(samples,expected):
            got=lib.probe_value(f,x,y);require(math.isfinite(got),'Nonfinite native math result')
            ulps=abs(ordered(target)-ordered(got)) if got!=target else 0
            maxima[FUNCTIONS[f]]=max(maxima[FUNCTIONS[f]],ulps)
            require(ulps<=1,f'{label} {FUNCTIONS[f]}({x!r},{y!r}) exceeds 1 ULP: {ulps}')
        record=provenance['profiles']['fma3' if mode else 'sse2'];corpus=HERE/'Reference'/record['path']
        require(sha(corpus)==record['sha256'],'Frozen original Windows math corpus changed')
        count=0
        with gzip.open(corpus,'rt',newline='') as stream:
            for r in csv.DictReader(stream):
                f=FUNCTIONS.index(r['function']);x=float(r['x']);y=float(r['y']);target=float(r['result'])
                require(bits(lib.probe_value(f,x,y))==bits(target),'Native primitive differs from original Windows '+r['function'])
                count+=1
        require(count==record['samples'],'Frozen primitive sample count changed')
        for f in (0,2):require(bits(lib.probe_value(f,-0.,0.))==bits(-0.),'Negative zero was lost')
        for f,x in ((0,math.inf),(1,-math.inf),(2,1.01)):
            lib.probe_clear();got=lib.probe_value(f,x,0.)
            require(math.isnan(got) and lib.probe_invalid() and lib.probe_errno()==errno.EDOM,'Incomplete native domain error handling')
        for x,target in ((math.inf,math.inf),(-math.inf,0.),(710.,math.inf),(-800.,0.)):
            lib.probe_clear()
            require(lib.probe_value(4,x,0.)==target,'Incorrect exponential range result')
            require(lib.probe_errno()==(errno.ERANGE if math.isfinite(x) else 0),'Incorrect exponential range errno')
        for f in (0,1,2,4):
            for nan,invalid in ((0x7ff8000000000042,False),(0x7ff0000000000042,True)):
                lib.probe_clear();got=lib.probe_bits(f,nan,0)
                require(bits(got)==0x7ff8000000000042 and bool(lib.probe_invalid())==invalid,'NaN payload/exception propagation failed')
        reports.append(dict(profile=label,windows_samples_exact=count,mpfr_samples=len(samples),maximum_ulps=maxima,edge_cases='passed'))
    report=dict(status='passed',automatic_profile=profile,equatorial_latitude_hex=latitude.hex(),probe_sha256=sha(a.probe),oracle=dict(version=lib.oracle_version().decode(),path=str(oracle),sha256=sha(oracle),precision_bits=[256,512]),maximum_allowed_ulps=1,profiles=reports)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
