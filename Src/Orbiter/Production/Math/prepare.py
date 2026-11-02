#!/usr/bin/env python3
"""Check pinned AMD sources and convert private assembly/header bindings for ELF.

Original numerical instructions and constants are retained. Every unrecognized
directive is passed to the assembler, which must reject unsupported syntax.
No Windows window, operating-system or public SDK emulation is involved.
"""
import argparse,hashlib,json,re
from pathlib import Path

ASSEMBLY=('cos','sin','remainder_piby2_forAsm','remainder_piby2_forFMA3','Lsincos_array','L2_by_pi_bits')

def assembly(text):
    aliases=dict(re.findall(r'(?im)^\s*(\w+)\s+TEXTEQU\s*<([^>]+)>',text))
    for a,b in aliases.items():text=re.sub(r'\b'+a+r'\b',b,text)
    text=re.sub(r'\bcos\b','aw_cos',text);text=re.sub(r'\bsin\b','aw_sin',text)
    memory=set(re.findall(r'(?im)^\s*(\w+)\s+(?:DQ|DD|DB)\s',text))|{'__Lcosarray','__Lsinarray','__use_fma3_lib','__L_2_by_pi_bits'}
    result=['.intel_syntax noprefix'];frame=None;function=False;equates={}
    for original in text.splitlines():
        code,_,comment=original.partition(';');s=code.strip()
        if not s:result.append('# '+comment);continue
        if re.match(r'(?:include|EXTRN|EXTERN|END\b|\w+\s+TEXTEQU|\.ENDPROLOG)',s,re.I):continue
        if re.match(r'\w+\s+ENDP\b',s,re.I):
            result.append('.cfi_endproc');frame=None;function=False;continue
        s=re.sub(r'\b([0-9][0-9a-fA-F]*)[hH]\b',lambda m:'0x'+m[1],s)
        if s.lower()=='.const':result.append('.section .rodata');continue
        if s.lower()=='.code':result.append('.text');continue
        if s.lower().startswith('align '):result.append('.balign '+s.split()[1]);continue
        m=re.match(r'(\w+)\s+EQU\s+(.+)',s,re.I)
        if m:
            equates[m[1]]=int(m[2],0);result.append('.equ '+m[1]+', '+m[2]);continue
        m=re.match(r'(\w+)\s+PROC(?:\s+FRAME)?',s,re.I)
        if m:
            result.append('.type '+m[1]+', @function\n'+m[1]+':\n.cfi_startproc');function=True;continue
        m=re.match(r'PUBLIC\s+(\w+)',s,re.I)
        if m:result.append('.globl '+m[1]+'\n.hidden '+m[1]);continue
        m=re.match(r'(?:(\w+)\s+)?(DQ|DD|DB)\s+(.+)',s,re.I)
        if m:
            if m[1]:result.append(m[1]+':')
            result.append({'DQ':'.quad','DD':'.long','DB':'.byte'}[m[2].upper()]+' '+m[3]);continue
        m=re.match(r'Stack(Allocate|Deallocate)\s+(\w+)',s,re.I)
        if m:
            allocate=m[1].lower()=='allocate'
            if equates[m[2]]:result.append(('sub' if allocate else 'add')+' rsp, '+m[2])
            if allocate:frame=m[2]
            result.append('.cfi_def_cfa_offset '+(m[2]+'+8' if allocate else '8'));continue
        m=re.match(r'(AVX)?(Save|Restore)Xmm\s+(\w+),\s*(\w+)',s,re.I)
        if m:
            op='vmovdqa' if m[1] else 'movdqa';memory_operand='XMMWORD PTR [rsp+'+m[4]+']'
            result.append(op+' '+(memory_operand+', '+m[3] if m[2].lower()=='save' else m[3]+', '+memory_operand));continue
        # MASM's MOVD alias for a 64-bit general register is the MOVQ encoding.
        if re.match(r'movd\s',s,re.I) and re.search(r'\br(?:ax|bx|cx|dx|[89]|1[0-5])\b',s):s=re.sub(r'^movd','movq',s,flags=re.I)
        label=re.match(r'\w+:$',s)
        if not label and not re.match(r'(?:j\w+|call)\s',s,re.I):
            for symbol in sorted(memory,key=len,reverse=True):
                s=re.sub(r'(?<![\w+\[])\b'+re.escape(symbol)+r'\b(?:\+(0x[0-9a-fA-F]+|\d+))?(?!\w)',
                         lambda m:'[rip+'+symbol+('+'+m[1] if m[1] else '')+']',s)
        result.append(s+(' # '+comment if comment else ''))
        if label and function and frame:result.append('.cfi_def_cfa_offset '+frame+'+8')
    if function:raise ValueError('Unclosed vendor assembly function')
    result.append('.section .note.GNU-stack,"",@progbits')
    return '\n'.join(result)+'\n'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();lock=json.loads((a.source/'sources.lock.json').read_text());a.output.mkdir(parents=True,exist_ok=True)
    for name,record in lock['files'].items():
        raw=(a.source/'amd'/name).read_bytes().replace(b'\r\n',b'\n')
        if hashlib.sha256(raw).hexdigest()!=record['sha256_lf']:raise ValueError('Pinned AMD source changed: '+name)
    for name in ASSEMBLY:
        (a.output/(name+'.s')).write_text(assembly((a.source/'amd'/(name+'.asm')).read_text()))
    for name in ('libm.h','libm_util.h','libm_inlines.h','libm_errno.h','asin.c','atan2.c'):
        text=(a.source/'amd'/name).read_text()
        if name=='libm.h':
            text=text.replace('#define FN_PROTOTYPE(fname) fname','#ifndef FN_PROTOTYPE\n#define FN_PROTOTYPE(fname) aw_##fname\n#endif')
            text=text.replace('#include <fpieee.h>','#include "NativeError.h"')
        if name=='libm_util.h':
            text=text.replace('#undef long\n#define long __int64','/* GNU LP64 already supplies the required 64-bit long. */')
        (a.output/name).write_text(text)
    # Generated C names agree with the C++ dispatcher, without changing vendor C.
    for profile in ('fma','sse2'):
        path=a.output/('asin_'+profile+'.c')
        path.write_text('#define FN_PROTOTYPE(name) orbiter_asin_'+profile+'\n#include "asin.c"\n')
    (a.output/'preparation.json').write_text(json.dumps(dict(source_commit=lock['commit'],source_archive_sha256=lock['archive_sha256'],
        syntax_and_private_bindings_only=True,files=lock['files']),indent=2)+'\n')
    print('Verified pinned AMD numerical sources and prepared native ELF bindings')
if __name__=='__main__':main()
