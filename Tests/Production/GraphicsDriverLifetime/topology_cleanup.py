"""A separate, byte-conserved Mesa CPU-topology allocation lifetime variant."""
import hashlib
from pathlib import Path
import json

ORIGINAL_SHA256='f25d4795da83bf12e39da4ef908b8f5e9ca689e5a6ae47e333b1a3de6ba82c97'
APPEND=b'''\n#if DETECT_OS_LINUX && (defined(__GNUC__) || defined(__clang__))
/* The topology cache belongs to this loaded driver, just like its CPU caps.
 * All contexts and worker threads must already be released before dlclose.
 * Release its sole heap allocation when that owner is finally unloaded.
 */
static void __attribute__((destructor))
util_cpu_detect_fini(void)
{
   free(util_cpu_caps.L3_affinity_mask);
   util_cpu_caps.L3_affinity_mask = NULL;
   _util_cpu_caps_state.caps.L3_affinity_mask = NULL;
}
#endif
'''


def candidate(original):
    if hashlib.sha256(original).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError('Exact original Mesa CPU detection source required')
    return original+APPEND


def apply(source):
    path=Path(source)/'src/util/u_cpu_detect.c';original=path.read_bytes();compiled=candidate(original)
    path.write_bytes(compiled)
    if path.read_bytes()!=compiled:raise ValueError('Actual topology cleanup source differs')
    return dict(protocol='mesa-26.0.8-cpu-topology-owner-cleanup-v1',source='src/util/u_cpu_detect.c',
        original_sha256=ORIGINAL_SHA256,compiled_sha256=hashlib.sha256(compiled).hexdigest(),
        only_change='Append Linux DSO finalizer freeing the original owned L3 affinity mask and clearing both aliases; all CPU detection, affinity selection and rendering code byte unchanged',
        appended_bytes=len(APPEND),cleanup_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
