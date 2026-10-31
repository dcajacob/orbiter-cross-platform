#!/usr/bin/env python3
"""Compare real client configurations using frozen budgets and full-image SSIM."""
import argparse
from array import array
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from behavior_suite import compare,rows
from mesa_runtime import require


def image_ssim(left,right,width,height):
    """RGB SSIM: 11x11 Gaussian (sigma 1.5), population covariance, valid crop.

    No overlay masks, rescaling, colour edits, or downsampling are applied.
    Identical bytes have SSIM 1 by definition. The slower path uses only the
    standard library so the comparison tool has no unpinned image dependency.
    """
    require(len(left)==len(right)==width*height*4,'invalid RGBA readback dimensions')
    if left==right:return 1.0
    weights=[math.exp(-i*i/(2*1.5**2)) for i in range(-5,6)]
    total=sum(weights);weights=[value/total for value in weights]
    c1=(.01*255)**2;c2=(.03*255)**2
    score=0.;samples=0
    for channel in range(3):
        a,b=left[channel::4],right[channel::4]
        planes=[array('d',[0.])*(width*height) for _ in range(5)]
        # Separable convolution of the five first/second moments.
        for y in range(height):
            for x in range(5,width-5):
                p=y*width+x;values=[0.]*5
                for dx,w in enumerate(weights):
                    av=a[p+dx-5];bv=b[p+dx-5]
                    values[0]+=w*av;values[1]+=w*bv
                    values[2]+=w*av*av;values[3]+=w*bv*bv;values[4]+=w*av*bv
                for plane,value in zip(planes,values):plane[p]=value
        for y in range(5,height-5):
            for x in range(5,width-5):
                p=y*width+x;values=[0.]*5
                for dy,w in enumerate(weights):
                    q=p+(dy-5)*width
                    for i in range(5):values[i]+=w*planes[i][q]
                u,v,aa,bb,ab=values
                va=max(0.,aa-u*u);vb=max(0.,bb-v*v);cov=ab-u*v
                score+=((2*u*v+c1)*(2*cov+c2))/((u*u+v*v+c1)*(va+vb+c2));samples+=1
    return score/samples


def projected_landmarks(directory):
    camera=rows(directory/'camera.csv')[0]
    position=[float(camera[k]) for k in ('px','py','pz')]
    rotation=[[float(camera[f'm{i}{j}']) for j in range(1,4)] for i in range(1,4)]
    tangent=math.tan(float(camera['aperture']));result={}
    for row in rows(directory/'scene.csv'):
        if row['object'] not in ('Earth','ISS','PB'):continue
        p=[float(row[k])-v for k,v in zip(('px','py','pz'),position)]
        local=[sum(rotation[i][j]*p[i] for i in range(3)) for j in range(3)]
        require(local[2]>0,'required landmark is behind the real camera: '+row['object'])
        result[row['object']]=(640+360*local[0]/(local[2]*tangent),360-360*local[1]/(local[2]*tangent))
    require(set(result)=={'Earth','ISS','PB'},'missing engine/camera landmarks')
    return result


def run(left,right):
    a=json.loads((left/'client-report.json').read_text());b=json.loads((right/'client-report.json').read_text())
    require(a['provenance']==b['provenance'],'client source/application/data provenance differs')
    require(a['renderer']==b['renderer'],'actual software renderer or window dimensions differ')
    require(a['asset_sha256']==b['asset_sha256'],'actual stock asset content differs')
    case=next(c for c in json.loads((HERE.parent/'behavior-cases.json').read_text())['cases'] if c['id']=='callbacks')
    numerical=compare(left,right,case)
    fields=('object','type','class','mesh','index','name','groups','materials','textures')
    identity=lambda path:[tuple(r[k] for k in fields) for r in rows(path/'scene.csv')]
    require(identity(left)==identity(right),'real scene object/mesh/material/texture identities differ')
    p,q=projected_landmarks(left),projected_landmarks(right)
    error=max(math.dist(p[name],q[name]) for name in p)
    require(error<=1.,'projected engine landmarks differ by more than one pixel')
    ssim=image_ssim((left/'scene.rgba').read_bytes(),(right/'scene.rgba').read_bytes(),1280,720)
    require(math.isfinite(ssim) and ssim>=.98,'full real-client image SSIM is below 0.98')
    return dict(status='passed',numerical=numerical,maximum_projected_landmark_error_px=error,
                landmarks_px=p,ssim=ssim,ssim_method='RGB 11x11 Gaussian sigma 1.5; population covariance; valid crop; no masks',
                provenance=a['provenance'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--debug',type=Path,required=True);parser.add_argument('--release',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    report=dict(status='pending')
    try:report=run(args.debug,args.release)
    except Exception as error:
        report.update(status='failed',error=str(error));raise
    finally:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
