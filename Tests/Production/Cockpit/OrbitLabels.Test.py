#!/usr/bin/env python3
"""Exercise the actual Orbit MFD formatter and Astro string helpers under ASan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


PREFIX = r'''
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
constexpr double AU = 1.49597870691e11, iAU = 1.0/AU, DEG = 180.0/3.141592653589793;
double Deg(double angle) { return angle*DEG; }
double posangle(double angle) { return angle; }
char *DistStr(double, int=4);
char *FloatStr(double, int=4);
// Read-only formatter inputs: propagation is deliberately outside this test.
struct Elements {
    double a=7e6,e=.1,i=.3,theta=.4,omegab=.5,sample=7e6;
    double SMi() const { return sample; }
    double PeDist() const { return sample; }
    double ApDist() const { return sample; }
    double Radius() const { return sample; }
    double OrbitT() const { return sample; }
    double PeT() const { return sample; }
    double ApT() const { return sample; }
    double Vel() const { return sample; }
    double ArgPer() const { return .2; }
    double TrueAnm() const { return .4; }
    double TrueLng() const { return .6; }
    double MeanAnm() const { return .7; }
    double MeanLng() const { return .8; }
};
namespace orbiter::production {
double OrbitDisplayTrueAnomaly(const Elements& el) { return el.TrueAnm(); }
double OrbitDisplayTrueLongitude(const Elements& el) { return el.TrueLng(); }
}
namespace oapi {
struct Sketchpad {
    vector<string> labels;
    void Text(int,int,const char* value,int size) { labels.emplace_back(value,size); }
};
}
struct Reference { double Size() const { return 6371000.; } };
struct Instrument_Orbit {
    static constexpr int DIST_RAD=0;
    int ch=12,dstmode=0;
    Reference body; Reference *elref=&body;
    void DisplayElements(oapi::Sketchpad*, const Elements*, int,int);
};
'''

MAIN = r'''
int main(int argc,char** argv) {
    try {
        const bool extreme=argc>1 && string(argv[1])=="extreme";
        Instrument_Orbit mfd;
        const vector<double> samples=extreme ? vector<double>{1e20,-1e20,1e100,-1e100,
            numeric_limits<double>::max(),-numeric_limits<double>::max()} :
            vector<double>{0.,.01,99.,100.,999.,1000.,1e4,1e7,1e10,1e13};
        for(double sample:samples) for(double eccentricity:{.1,1.2}) for(int mode:{0,1}) {
            Elements el;el.sample=sample;el.e=eccentricity;el.a=sample;
            mfd.dstmode=mode;oapi::Sketchpad skp;
            mfd.DisplayElements(&skp,&el,0,0);
            if(skp.labels.size()!=18) throw runtime_error("Complete original Orbit label list missing");
            for(const auto& text:skp.labels) {
                if(text.empty() || text.size()>=512) throw runtime_error("Missing or overlong Orbit label");
                cout<<text<<'\n';
            }
            if(extreme && sample>1e19) {
                char expected[512];snprintf(expected,sizeof expected,"Rad% 0.0fAU",sample*iAU);
                if(mode==0 && skp.labels[4]!=expected) throw runtime_error("Large distance text was truncated or changed");
            }
        }
        if(extreme) {
            for(double sample:{numeric_limits<double>::max(),-numeric_limits<double>::max()}) {
                char expected[512];snprintf(expected,sizeof expected,"% 0.0fAU",sample*iAU);
                if(string(DistStr(sample))!=expected) throw runtime_error("Extreme finite distance text changed");
            }
        }
        oapi::Sketchpad empty;mfd.DisplayElements(&empty,nullptr,0,0);
        if(empty.labels!=vector<string>{"Orbital","Elements","not","available"})
            throw runtime_error("Unavailable elements text changed");
    } catch(const exception& error) { cerr<<error.what()<<'\n';return 1; }
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();root=a.source_root.resolve();out=a.output.resolve()
    assert not out.exists();out.mkdir(parents=True)
    inputs={name:(root/name).read_bytes() for name in ('Src/Orbiter/MfdOrbit.cpp','Src/Orbiter/Astro.cpp')}
    mfd=inputs['Src/Orbiter/MfdOrbit.cpp'].decode('cp1252')
    mfd=mfd[mfd.index('void Instrument_Orbit::DisplayElements ('):mfd.index('int Instrument_Orbit::ProcessMessage (')]
    astro=inputs['Src/Orbiter/Astro.cpp'].decode('cp1252')
    astro=astro[astro.index('static char strbuf['):astro.index('char *SciStr (')]
    assert mfd.count('char cbuf[512];')==1 and astro.count('static char strbuf[512];')==1
    compiler=shutil.which('c++');assert compiler
    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
             UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    env.pop('LD_PRELOAD',None)
    results={}
    for name,body,arguments in (
        ('current-ordinary',mfd+astro,[]),
        ('original-ordinary',mfd.replace('char cbuf[512];','char cbuf[16];')+
         astro.replace('static char strbuf[512];','static char strbuf[256];'),[]),
        ('current-extreme',mfd+astro,['extreme']),
        ('original-label-overflow',mfd.replace('char cbuf[512];','char cbuf[16];')+astro,['extreme']),
        ('original-distance-overflow',mfd+astro.replace('static char strbuf[512];','static char strbuf[256];'),['extreme'])):
        source=out/(name+'.cpp');source.write_text(PREFIX+body+MAIN,encoding='cp1252')
        exe=out/name
        argv=[compiler,'-std=c++17','-O1','-g','-finput-charset=WINDOWS-1252',
              '-fsanitize=address,undefined','-fno-omit-frame-pointer',str(source),'-o',str(exe)]
        with (out/(name+'-build.log')).open('w') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True)
        with (out/(name+'.stdout')).open('wb') as stdout,(out/(name+'.stderr')).open('wb') as stderr:
            r=subprocess.run([str(exe),*arguments],env=env,stdout=stdout,stderr=stderr)
        results[name]=dict(actual_exitcode=r.returncode,argv=argv)
        if name.startswith('original-') and name.endswith('overflow'):
            assert r.returncode!=0 and b'AddressSanitizer' in (out/(name+'.stderr')).read_bytes(),name
        else:assert r.returncode==0,name
    assert (out/'current-ordinary.stdout').read_bytes()==(out/'original-ordinary.stdout').read_bytes()
    assert all((root/n).read_bytes()==v for n,v in inputs.items())
    report=dict(status='passed-actual-Orbit-and-Astro-formatters',ordinary_label_sets=40,
                extreme_label_sets=24,ordinary_text_byte_identical=True,original_overflow_controls=2,
                source_sha256={n:hashlib.sha256(v).hexdigest() for n,v in inputs.items()},
                source_unchanged=True,controls=results,physics_qualified=False,phase6_complete=False)
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'])


if __name__=='__main__':main()
