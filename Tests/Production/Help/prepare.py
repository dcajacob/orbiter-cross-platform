#!/usr/bin/env python3
"""Build browser-readable stock help from the original HTML and LDoc sources.

Development provisioner, not the Phase 8 installer. Original inputs are copied
verbatim; only URL/encoding adaptations are made in the browser copies.
"""
import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import subprocess
import tempfile
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
WEB = {'.htm', '.html', '.css', '.js', '.jpg', '.jpeg', '.gif', '.png', '.svg', '.hhc', '.hhk'}
ATTR = re.compile(r'(?P<prefix>\b(?:href|src|background)\s*=\s*)(?P<q>[\"\'])(?P<url>.*?)(?P=q)', re.I)


def decode(data):
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return data.decode('cp1252')


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.title = []; self.hidden = 0; self.in_title = False
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
        if tag == 'title': self.in_title = True
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
        if tag == 'title': self.in_title = False
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)
        if self.in_title: self.title.append(data)


class Sitemap(HTMLParser):
    def __init__(self):
        super().__init__(); self.entries = []; self.item = None; self.depth = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'ul': self.depth += 1
        if tag == 'object' and attrs.get('type', '').lower() == 'text/sitemap':
            self.item = {'depth': max(0, self.depth - 1)}
        if tag == 'param' and self.item is not None:
            self.item[attrs.get('name', '').lower()] = attrs.get('value', '')
    def handle_endtag(self, tag):
        if tag == 'ul': self.depth = max(0, self.depth - 1)
        if tag == 'object' and self.item is not None:
            if self.item.get('name'): self.entries.append(self.item)
            self.item = None


def options(project):
    section = ''; result = {}
    for line in decode(project.read_bytes()).splitlines():
        if line.startswith('['): section = line.lower()
        elif section == '[options]' and '=' in line:
            key, value = line.split('=', 1); result[key.lower()] = value
    return result


def generated_docs(lua, work):
    env = dict(os.environ)
    env['LUA_PATH'] = str(ROOT/'Extern/Penlight/lua/?.lua')+';'+str(ROOT/'Extern/Penlight/lua/?/init.lua')+';;'
    env['LUA_CPATH'] = str(lua.parent/'doc-tools/?.so')+';;'
    vessels = {}
    for vessel, variable in (('DeltaGlider', '${dgsrc}'), ('ShuttleA', '${srcdir}')):
        folder = work/vessel; folder.mkdir()
        source = ROOT/'Src/Vessel'/vessel
        config = (source/'Help/config.ld.in').read_text().replace(variable, source.as_posix())
        (folder/'config.ld').write_text(config)
        vessels[vessel] = folder
    interpreter = work/'interpreter'; interpreter.mkdir()
    source = ROOT/'Src/Module/LuaScript/LuaInterpreter'
    for path in source.iterdir():
        if path.suffix in ('.h', '.cpp', '.ld', '.md', '.lua'):
            # The original config names interpreter.cpp in lowercase.
            shutil.copyfile(path, interpreter/path.name.lower())
    for folder in (*vessels.values(), interpreter):
        # Interpreter.cpp defines multiple classes/modules and revisits oapi.
        subprocess.run([str(lua), str(ROOT/'Extern/ldoc/ldoc.lua'), '--multimodule', '--merge', '.'], cwd=folder, env=env, check=True)
    return {name: folder/'lua' for name, folder in vessels.items()}, interpreter/'out'


def prepare(destination, lua):
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='orbiter-help-') as temporary:
        vessel_lua, api = generated_docs(lua, Path(temporary))
        books = {}
        projects = sorted((ROOT/'Html').rglob('*.hhp'))
        projects += sorted((ROOT/'Src/Vessel').glob('*/Help/*.hhp'))
        projects += [ROOT/'Src/Vessel/DeltaGlider/Help/AAP/aap.hhp', ROOT/'Src/Plugin/ScnEditor/Help/ScnEditor.hhp']
        for project in projects:
            opt = options(project)
            cmake = (project.parent/'CMakeLists.txt').read_text()
            subdir = re.search(r'set\(subdir\s+([^\s)]+)\)', cmake)
            compiled = PurePosixPath(opt['compiled file'].replace('\\', '/')).name
            key = ('html/'+(subdir[1]+'/' if subdir else '')+compiled).lower()
            files = {p.relative_to(project.parent).as_posix().lower(): p for p in project.parent.rglob('*') if p.is_file() and p.suffix.lower() in WEB}
            # Shared resources are copied by the Windows help build as well.
            for name in ('Orbiter.css', 'master.js'):
                files.setdefault(name.lower(), ROOT/'Html'/name)
            for vessel, generated in vessel_lua.items():
                if project.parent == ROOT/'Src/Vessel'/vessel/'Help':
                    files.update({'lua/'+p.relative_to(generated).as_posix().lower(): p for p in generated.rglob('*') if p.is_file()})
            books[key] = dict(options=opt, project=project, files=files)
        project = ROOT/'Src/Module/LuaScript/LuaInterpreter/interpreter.hhp'
        books['html/script/api/reference.chm'] = dict(options=options(project), project=project,
            files={p.relative_to(api).as_posix().lower(): p for p in api.rglob('*') if p.is_file()})
        def folder(key): return 'books/'+key[5:-4]
        inputs = [ROOT/'Src/Vessel/DeltaGlider/DGLua.cpp', ROOT/'Src/Vessel/ShuttleA/ShuttleALua.cpp']
        for directory in (ROOT/'Extern/ldoc', ROOT/'Extern/Penlight', ROOT/'Extern/luafilesystem',
                          ROOT/'Src/Module/LuaScript/LuaInterpreter'):
            inputs.extend(p for p in directory.rglob('*') if p.is_file() and p.suffix in ('.lua', '.cpp', '.c', '.h', '.ld', '.md'))
        inputs.extend(ROOT/'Src/Vessel'/name/'Help/config.ld.in' for name in ('DeltaGlider', 'ShuttleA'))
        manifest = {'books': {}, 'sources': {}, 'unresolved_links': [],
            'generator_inputs': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)},
            'lua_sha256': hashlib.sha256(lua.read_bytes()).hexdigest(),
            'lfs_sha256': hashlib.sha256((lua.parent/'doc-tools/lfs.so').read_bytes()).hexdigest()}

        catalog = []
        for key, book in books.items():
            opt, files = book['options'], book['files']
            default = opt['default topic'].replace('\\', '/').lower().lstrip('/')
            if default not in files: raise ValueError('Missing default help topic: '+key+'::'+default)
            base = destination/folder(key); base.mkdir(parents=True, exist_ok=True)
            catalog.append('\t'.join((key, 'Help/'+folder(key)+'/_viewer.html', default)))
            if key == 'html/script/api/reference.chm':
                catalog.append('\t'.join(('orbitersdk/doc/orbiter_lua.chm', 'Help/'+folder(key)+'/_viewer.html', default)))
            manifest['books'][key] = {'project': str(book['project'].relative_to(ROOT)), 'default': default, 'files': len(files)}
            def link(value, page):
                value = html.unescape(value).replace('\\', '/')
                if '::' in value:
                    chm, topic = value.split('::', 1)
                    chm = re.sub(r'^(?:ms-its:|mk:@MSITStore:)', '', chm, flags=re.I).lower()
                    target = chm if chm.startswith('html/') else posixpath.normpath(posixpath.join(posixpath.dirname(key), chm))
                    if target not in books:
                        manifest['unresolved_links'].append([key, page, value]); return value
                    topic = topic.lstrip('/') or books[target]['options']['default topic']
                    parsed = urlsplit(topic)
                    name = unquote(parsed.path).lower()
                    if name not in books[target]['files'] and name.startswith('html/'): name = name[5:]
                    if name not in books[target]['files']: manifest['unresolved_links'].append([key, page, value])
                    relative = posixpath.relpath(folder(target)+'/_viewer.html', posixpath.dirname(folder(key)+'/'+page))
                    return relative+'?topic='+quote(name+('#'+parsed.fragment if parsed.fragment else ''), safe='')
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc or not parsed.path: return value
                if value == 'www.lua.org': return 'https://www.lua.org/'
                if value == 'cam_target.htm' and key == 'html/orbiter.chm': value = 'cam_mode.htm'; parsed = urlsplit(value)
                name = posixpath.normpath(posixpath.join(posixpath.dirname(page), unquote(parsed.path))).lower()
                if name not in files and PurePosixPath(name).name in ('orbiter.css', 'master.js'): name = PurePosixPath(name).name
                if name not in files and parsed.path.lower() in files: name = parsed.path.lower()
                if name not in files and re.search(r'\bname=[\"\']'+re.escape(value)+r'[\"\']', decode(files[page].read_bytes()), re.I):
                    return '#'+value
                if name not in files:
                    manifest['unresolved_links'].append([key, page, value]); return value
                relative = posixpath.relpath(name, posixpath.dirname(page) or '.')
                return quote(relative, safe='/')+('?' + parsed.query if parsed.query else '')+('#'+parsed.fragment if parsed.fragment else '')
            pages = []
            for name, source in sorted(files.items()):
                data = source.read_bytes()
                original = destination/'sources'/key[5:-4]/name
                original.parent.mkdir(parents=True, exist_ok=True); original.write_bytes(data)
                generated = not source.is_relative_to(ROOT)
                manifest['sources'][original.relative_to(destination).as_posix()] = {
                    'source': 'original LDoc output' if generated else source.relative_to(ROOT).as_posix(),
                    'sha256': hashlib.sha256(data).hexdigest()}
                out = base/name; out.parent.mkdir(parents=True, exist_ok=True)
                if source.suffix.lower() in ('.htm', '.html', '.hhc', '.hhk', '.css', '.js'):
                    content = decode(data)
                    if source.suffix.lower() in ('.htm', '.html'):
                        # Two malformed original links prevent browser navigation.
                        # The byte-for-byte inputs remain under sources/.
                        if key == 'html/orbiter.chm' and name == 'camera.htm':
                            content = content.replace('href="cam_mode.htm>', 'href="cam_mode.htm">')
                        if key == 'html/orbiter.chm' and name == 'script/api_oapi.htm':
                            content = content.replace('<a href="oapi_get_fuelmass"></a>', '<a name="oapi_get_fuelmass"></a>')
                        document = Text(); document.feed(content)
                        pages.append({'topic': name, 'title': ' '.join(document.title).strip() or name,
                            'text': ' '.join(' '.join(document.parts).split())})
                        content = ATTR.sub(lambda m: m['prefix']+m['q']+html.escape(link(m['url'], name), quote=True)+m['q'], content)
                        content = re.sub(r'charset\s*=\s*windows-1252', 'charset=utf-8', content, flags=re.I)
                        # All sources are now UTF-8, including pages without a charset.
                        content = re.sub(r'(<head\b[^>]*>)', r'\1<meta charset="utf-8">', content, count=1, flags=re.I)
                        # A CHM jump opens the destination book at the top level.
                        content = re.sub(r'(<a\b[^>]*href=[\"\'][^\"\']*_viewer\.html\?[^>]*)(>)', r'\1 target="_top"\2', content, flags=re.I)
                    elif source.suffix.lower() == '.css':
                        content = re.sub(r'url\(([^)]+)\)', lambda m: 'url("'+link(m[1].strip(' \"\''), name)+'")', content, flags=re.I)
                    out.write_text(content, encoding='utf-8')
                else: out.write_bytes(data)
            navigation = {}
            for field, label in (('contents file', 'contents'), ('index file', 'index')):
                path = opt.get(field, '').replace('\\', '/').lower()
                parsed = Sitemap()
                if path:
                    if path not in files: raise ValueError('Missing help navigation: '+key+'::'+path)
                    parsed.feed(decode(files[path].read_bytes()))
                navigation[label] = [dict(title=e['name'], topic=link(e.get('local',''), path), depth=e['depth']) for e in parsed.entries]
            data = dict(title=opt.get('title', next(p['title'] for p in pages if p['topic']==default)), default=default, pages=pages, **navigation)
            (base/'_catalog.js').write_text('"use strict";\nconst helpBook = '+json.dumps(data, ensure_ascii=True)+';\n', encoding='utf-8')
            for name in ('viewer.html', 'viewer.js', 'viewer.css'):
                shutil.copyfile(ROOT/'Html/Native'/name, base/('_'+name))
        (destination/'catalog.tsv').write_text('\n'.join(catalog)+'\n', encoding='utf-8')
        (destination/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
        print('Prepared', len(books), 'original help books;', len(manifest['unresolved_links']), 'unresolved original links (see manifest.json)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True, help='Assets/Help directory')
    parser.add_argument('--lua', type=Path, required=True, help='Native build native-lua/lua executable, with doc-tools/lfs.so')
    args = parser.parse_args()
    prepare(args.destination.resolve(), args.lua.resolve())
