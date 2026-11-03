#!/usr/bin/env python3
"""Prove the VC image gate selects actual display pixels and catches a local defect."""
import argparse
import csv
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parent/'CockpitCamera'))
from run import crop,digest,image_ssim,mfd_quads,project_quad,require,rows,text_values,visible_bounds

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();require(not args.output.exists(),'Camera gate result exists')
    pose=next(row for row in rows(args.capture/'camera-sdk.csv') if row['tick']=='50')
    image=args.capture/'instrument-50.rgba';before=digest(image);pixels=image.read_bytes()
    # Known logical pixel coordinates encoded in a bottom-origin OpenGL image.
    encoded=bytes(v for y in reversed(range(720)) for x in range(1280) for v in (x%256,y%256,17,255))
    bounds={}
    for name,quad in mfd_quads().items():
        points=project_quad(quad,pose)
        require(all(0<=x<1280 and 0<=y<720 for x,y in points),'Both actual MFD displays must be visible')
        bounds[name]=visible_bounds(points);x0,y0,x1,y1=bounds[name]
        selected=crop(encoded,bounds[name])
        require(selected[:4]==bytes((x0%256,(y1-1)%256,17,255)) and
                selected[-4:]==bytes(((x1-1)%256,y0%256,17,255)),
                'Window projection and OpenGL readback origins disagree')
    left=bounds['LMFD_DISPLAY'];x0,y0,x1,y1=left
    changed=bytearray(pixels)
    for y in range(y0+30,y0+130):
        for x in range(x0+91,x0+111):
            offset=4*(1280*(719-y)+x);changed[offset:offset+4]=b'\xff\xff\xff\xff'
    whole=image_ssim(pixels,changed,1280,720)
    local=image_ssim(crop(pixels,left),crop(changed,left),x1-x0,y1-y0)
    require(whole>=.98 and local<.98,'On-screen MFD gate did not catch a defect hidden by whole-frame similarity')
    # Surface labels may change; every meaningful drawing field must survive.
    source=rows(args.capture/'instrument-text.csv')[:4]
    with tempfile.TemporaryDirectory(prefix='orbiter-text-label-test-') as temporary:
        out=Path(temporary)
        def project(values):
            with (out/'instrument-text.csv').open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
            return text_values(out).read_bytes()
        expected=project(source)
        require(project([{**row,'surface':str(int(row['surface'])+10000)} for row in source])==expected,
                'Opaque surface labels changed semantic drawing values')
        for field in ('frame','seconds','width','height','x','y','font_height','color','text_hex'):
            modified=[dict(row) for row in source];modified[0][field]+='1'
            require(project(modified)!=expected,'Meaningful drawing-field mutation was hidden: '+field)
    require(digest(image)==before,'Camera gate test modified the source image')
    report=dict(status='passed gate negative controls; not original Windows parity',source_image_sha256=before,
                exact_crop_corners_verified=True,meaningful_text_mutations_detected=9,
                whole_frame_ssim=whole,screen_mfd_ssim=local,existing_minimum=.98,bounds=bounds)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
