"""Read PE import/export names for explicit app/Mesa C dependency binding."""
import struct

class PE:
    def __init__(self,path):
        self.data=path.read_bytes();d=self.data
        pe=struct.unpack_from('<I',d,0x3c)[0]
        if d[pe:pe+4]!=b'PE\0\0':raise ValueError('invalid PE image')
        count=struct.unpack_from('<H',d,pe+6)[0];size=struct.unpack_from('<H',d,pe+20)[0]
        opt=pe+24;magic=struct.unpack_from('<H',d,opt)[0]
        if magic not in (0x10b,0x20b):raise ValueError('unsupported PE image')
        self.width=8 if magic==0x20b else 4;self.directory=opt+(112 if self.width==8 else 96)
        self.sections=[struct.unpack_from('<IIII',d,opt+size+40*i+8) for i in range(count)]
    def offset(self,rva):
        for virtual_size,start,raw_size,raw in self.sections:
            if start<=rva<start+max(virtual_size,raw_size):return raw+rva-start
        if rva<len(self.data):return rva
        raise ValueError('PE RVA outside file')
    def string(self,rva):
        start=self.offset(rva);return self.data[start:self.data.index(b'\0',start)].decode('ascii')
    def imports(self):
        rva,size=struct.unpack_from('<II',self.data,self.directory+8)
        if not rva:return {}
        result={};index=self.offset(rva)
        while True:
            original,_,_,name,first=struct.unpack_from('<IIIII',self.data,index);index+=20
            if not name:break
            symbols=set();thunk=self.offset(original or first)
            while True:
                value=struct.unpack_from('<Q' if self.width==8 else '<I',self.data,thunk)[0];thunk+=self.width
                if not value:break
                if value>>(self.width*8-1):
                    symbols.add('#ordinal:'+str(value&((1<<(self.width*8-1))-1)));continue
                symbols.add(self.string(value+2))
            result[self.string(name).casefold()]=symbols
        return result
    def exports(self):
        rva,size=struct.unpack_from('<II',self.data,self.directory)
        if not rva:return set()
        off=self.offset(rva);count=struct.unpack_from('<I',self.data,off+24)[0];names=self.offset(struct.unpack_from('<I',self.data,off+32)[0])
        return {self.string(struct.unpack_from('<I',self.data,names+i*4)[0]) for i in range(count)}
