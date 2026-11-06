"""Allow only retirement of cached world handles after all MFDs are destroyed."""

FIELDS = {
    'MfdOrbit.h': ('Instrument_Orbit', ('usr', 'elref', 'tgt')),
    'MfdMap.h': ('Instrument_Map', ('usr', 'ref', 'sel')),
    'MfdMap_old.h': ('Instrument_MapOld', ('usr', 'ref', 'btgt', 'otgt')),
    'MfdDocking.h': ('Instrument_Docking', ('usr', 'Legacy_ref')),
    'MfdLanding.h': ('Instrument_Landing', ('usr',)),
    'MfdHsi.h': ('Instrument_HSI', ('usr',)),
    'MfdAlign.h': ('Instrument_OPlaneAlign', ('usr', 'elref', 'tgt')),
    'MfdSync.h': ('Instrument_OSync', ('usr', 'tgt')),
    'MfdTransfer.h': ('Instrument_Transfer', ('usr', 'elref', 'src', 'tgt')),
}


def declaration(name):
    body = ' '.join('saveprm.' + field + (' = {};' if field == 'sel' else ' = nullptr;') for field in FIELDS[name][1])
    return '\tstatic void InvalidateWorldCache() { ' + body + ' }\n'


def cleanup_block():
    result = '\t// All MFDs are destroyed before this world boundary. Cached object\n\t// addresses must not restore handles from a retired world after reuse.\n'
    for name, (kind, fields) in FIELDS.items():
        call = '\t' + kind + '::InvalidateWorldCache();\n'
        result += '#ifdef _WIN32\n' + call + '#endif\n' if name == 'MfdMap_old.h' else call
    return result + '\n'


def restore_world_cache(source, name):
    expected = cleanup_block() if name == 'Mfd.cpp' else declaration(name) if name in FIELDS else None
    if expected is None:
        return source
    if source.count(expected) != 1:
        raise ValueError('World-owned MFD cache cleanup differs: ' + name)
    if name == 'Mfd.cpp':
        boundary = 'void Instrument::GlobalExit (oapi::CockpitClient *gc)\n{\n' + expected
        if source.count(boundary) != 1:
            raise ValueError('MFD cache retirement moved from the world boundary')
    else:
        start = source.index('class ' + FIELDS[name][0])
        public = source.index('public:\n', start) + len('public:\n')
        if not source[public:].startswith(expected):
            raise ValueError('MFD cache retirement declaration moved: ' + name)
    return source.replace(expected, '', 1)
