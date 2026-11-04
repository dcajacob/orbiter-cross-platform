"""Read complete actual saved scenarios without discarding module state fields."""
from decimal import Decimal,InvalidOperation
import hashlib
from pathlib import Path
import re

BEGIN=re.compile(r'^BEGIN_([A-Z0-9_]+)(?:\s+(.+))?$')


def require(value,message):
    if not value:raise ValueError(message)


def parse_saved(path):
    path=Path(path);body=path.read_bytes();lines=body.decode('cp1252').splitlines()
    require(lines.count('BEGIN_SHIPS')==lines.count('END_SHIPS')==1,'Saved scenario must contain one complete ship list')
    first=lines.index('BEGIN_SHIPS');last=lines.index('END_SHIPS')
    require(first<last,'Saved ship-list boundaries reversed')
    ships={};folded=set();index=first+1
    while index<last:
        line=lines[index];index+=1
        if not line.strip():continue
        require(not line[0].isspace() and ':' in line,'Saved vessel declaration missing')
        name,kind=line.split(':',1);kind=kind.strip()
        require(name==name.strip() and name and kind and not any(c.isspace() for c in kind) and name.casefold() not in folded,
                'Invalid or duplicate saved vessel declaration')
        folded.add(name.casefold());records=[]
        while index<last and lines[index].strip()!='END':
            raw=lines[index];value=raw.strip();index+=1
            if value and not raw[0].isspace() and ':' in value:
                head,tail=value.split(':',1)
                require(not head or not tail.strip() or any(c.isspace() for c in tail.strip()),
                        'Saved vessel END delimiter missing before another declaration')
            if value:records.append(value.split())
        require(index<last,'Saved vessel lacks its END delimiter');index+=1
        ships[name]=dict(class_name=kind,records=records)
    require(ships,'Saved scenario contains no actual vessels')
    outside=lines[:first]+lines[last+1:];blocks=[];loose=[];index=0
    while index<len(outside):
        line=outside[index].strip();index+=1
        if not line:continue
        begin=BEGIN.fullmatch(line)
        if not begin:
            require(not line.startswith('END_'),'Unmatched saved scenario block end')
            loose.append(line.split());continue
        tag=begin[1];stack=[tag];records=[]
        while index<len(outside) and stack:
            value=outside[index].strip();index+=1
            nested=BEGIN.fullmatch(value)
            if nested:stack.append(nested[1])
            elif value.startswith('END_'):
                require(value=='END_'+stack[-1],'Saved scenario block delimiters differ')
                stack.pop()
                if not stack:break
            if value:records.append(value.split())
        require(not stack,'Saved scenario block is incomplete')
        blocks.append(dict(header=line,records=records))
    def unique(tag):
        values=[block for block in blocks if block['header']==tag]
        require(len(values)==1,'Missing or repeated '+tag+' block');return values[0]['records']
    environment=unique('BEGIN_ENVIRONMENT');focus=unique('BEGIN_FOCUS')
    systems=[row[1] for row in environment if len(row)==2 and row[0]=='System']
    dates=[row[2] for row in environment if len(row)==3 and row[:2]==['Date','MJD']]
    targets=[' '.join(row[1:]) for row in focus if len(row)>=2 and row[0]=='Ship']
    require(len(systems)==len(dates)==len(targets)==1 and targets[0] in ships,'Saved environment/date/focus is incomplete')
    try:date=Decimal(dates[0])
    except InvalidOperation as error:raise ValueError('Saved date is not numeric') from error
    require(date.is_finite(),'Saved date is not finite')
    return dict(sha256=hashlib.sha256(body).hexdigest(),sha256_lf=hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest(),
                system=systems[0],mjd=dates[0],focus=targets[0],blocks=blocks,ships=ships,outside_records=loose)


def content_differences(left,right,description_blocks=()):
    """Report exact semantic-token differences; no numeric tolerance is inferred."""
    result=[]
    for name in ('system','mjd','focus','outside_records'):
        if left[name]!=right[name]:result.append(dict(path=name,left=left[name],right=right[name]))
    for name in sorted(set(left['ships'])|set(right['ships'])):
        a=left['ships'].get(name);b=right['ships'].get(name)
        if a is None or b is None:
            result.append(dict(path='ships/'+name,left=a,right=b));continue
        if a['class_name']!=b['class_name']:
            result.append(dict(path='ships/'+name+'/class',left=a['class_name'],right=b['class_name']))
        for index in range(max(len(a['records']),len(b['records']))):
            x=a['records'][index] if index<len(a['records']) else None
            y=b['records'][index] if index<len(b['records']) else None
            if x!=y:result.append(dict(path='ships/'+name+'/records/'+str(index),left=x,right=y))
    blocks=lambda value:[block for block in value['blocks'] if block['header'] not in description_blocks]
    a=blocks(left);b=blocks(right)
    for index in range(max(len(a),len(b))):
        x=a[index] if index<len(a) else None;y=b[index] if index<len(b) else None
        if x!=y:result.append(dict(path='blocks/'+str(index),left=x,right=y))
    return result
