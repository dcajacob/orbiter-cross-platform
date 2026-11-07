"""Stage exact guarded inputs across declared local volumes without per-run copies.

The canonical source remains in its frozen package. A verified private cache on
the output volume permits local hardlinks even when that package lives on C:.
Only explicitly guarded input hashes may enter this cache. Historical v1 remains
unchanged for its original same-volume evidence.
"""
import hashlib
import os
from pathlib import Path
import shutil
import threading

PROTOCOL = 'phase6-guarded-local-staging-v2'


def require(value, message):
    if not value: raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()


class BinaryLinks:
    def __init__(self, inputs, output):
        self.original = shutil.copy2
        self.output = Path(output).resolve()
        require(self.output.is_dir(), 'Existing fresh local output root required')
        self.cache = self.output / 'immutable-input-cache-v2'
        require(not self.cache.exists(), 'Fresh immutable input cache required')
        self.inputs = {os.path.normcase(str(Path(p).resolve())): (Path(p).resolve(), value)
                       for p, value in inputs.items()}
        require(all(sha(p) == value for p, value in self.inputs.values()), 'Guarded staging source differs')
        require(all(not p.is_relative_to(self.output) for p, value in self.inputs.values()),
                'Guarded input overlaps writable output')
        self.lock = threading.RLock()
        self.cached = {}
        self.links = []
        self.link_count = 0
        self.linked_inputs = {}
        self.fallback = []
        self.installed = False

    def same_volume(self, source, target):
        return source.stat().st_dev == target.parent.stat().st_dev

    def cached_source(self, source, checksum):
        with self.lock:
            self.cache.mkdir(exist_ok=True)
            target = self.cache / checksum
            require(sha(source) == checksum, 'Canonical input changed before cache copy')
            if target.exists():
                require(sha(target) == checksum, 'Immutable staging cache changed')
            else:
                temporary = target.with_suffix('.tmp')
                require(not temporary.exists(), 'Incomplete staging cache copy retained')
                self.original(source, temporary)
                require(sha(temporary) == checksum and sha(source) == checksum,
                        'Input or copied cache bytes changed')
                temporary.rename(target)
            self.cached[str(target)] = checksum
            return target

    def copy2(self, source, destination, *, follow_symlinks=True):
        incoming, target = Path(source).resolve(), Path(destination)
        if target.is_dir(): target = target / incoming.name
        resolved = target.resolve()
        require(incoming != resolved, 'Refusing staging copy onto its source')
        require(not target.is_symlink() and
                (not target.absolute().is_relative_to(self.output) or resolved.is_relative_to(self.output)),
                'Staging target is a symlink or escapes its declared output')
        require(os.path.normcase(str(resolved)) not in self.inputs, 'Cannot overwrite a guarded canonical input')
        inside = resolved.is_relative_to(self.output) and resolved != self.output
        key = os.path.normcase(str(incoming))
        if inside and target.exists():
            # A staged config or DLL may be a hardlink; detach it before a
            # private replacement, including ordinary unguarded copies.
            target.unlink()
        if not inside or key not in self.inputs or not follow_symlinks:
            return self.original(source, target, follow_symlinks=follow_symlinks)
        checksum = self.inputs[key][1]
        require(sha(incoming) == checksum, 'Canonical staged input changed')
        linked = incoming if self.same_volume(incoming, target) else self.cached_source(incoming, checksum)
        try:
            os.link(linked, target)
        except OSError as error:
            self.fallback.append(dict(source=str(incoming), target=str(target),
                error_type=type(error).__name__, winerror=getattr(error, 'winerror', None)))
            self.original(linked, target)
        else:
            require(target.stat().st_ino == linked.stat().st_ino, 'Actual local hardlink identity differs')
            with self.lock:
                self.link_count += 1
                self.linked_inputs[str(incoming)] = self.linked_inputs.get(str(incoming), 0) + 1
                if len(self.links) < 128:
                    self.links.append(dict(source=str(incoming), target=str(target), linked_source=str(linked),
                        sha256=checksum, source_file_id=incoming.stat().st_ino, local_file_id=target.stat().st_ino,
                        source_device=incoming.stat().st_dev, target_device=target.stat().st_dev))
        require(sha(target) == checksum, 'Staged input bytes differ')
        return str(target)

    def install(self):
        require(not self.installed and shutil.copy2 is self.original, 'Another staging adapter is installed')
        shutil.copy2 = self.copy2
        self.installed = True

    def close(self):
        if self.installed:
            shutil.copy2 = self.original
            self.installed = False
        require(all(sha(p) == value for p, value in self.inputs.values()), 'Canonical staging input changed')
        require(all(sha(p) == value for p, value in self.cached.items()), 'Immutable staging cache changed')

    def receipt(self):
        return dict(protocol=PROTOCOL, guarded_inputs=len(self.inputs),
                    cache_files_sha256=dict(self.cached), actual_link_count=self.link_count,
                    linked_input_counts=dict(self.linked_inputs), link_samples=list(self.links),
                    link_sample_limit=128, fallback=list(self.fallback))

    def controls(self, provider):
        source = Path(provider) / 'opengl32.dll'
        require(os.path.normcase(str(source.resolve())) in self.inputs, 'Pinned provider input missing')
        folder = self.output / 'local-staging-controls-v2'
        require(not folder.exists(), 'Fresh real staging controls required')
        folder.mkdir()
        ordinary, linked = folder / 'ordinary-copy.dll', folder / 'local-link.dll'
        self.original(source, ordinary)
        self.copy2(source, linked)
        checksum = self.inputs[os.path.normcase(str(source.resolve()))][1]
        require(sha(ordinary) == sha(linked) == checksum, 'Actual staging byte-equivalence control failed')
        local_source = Path(self.links[-1]['linked_source']) if self.links else source
        require(linked.stat().st_dev == local_source.stat().st_dev and
                linked.stat().st_ino == local_source.stat().st_ino and
                ordinary.stat().st_ino != local_source.stat().st_ino,
                'Actual local staging link/copy identities differ')
        return dict(status='passed-real-local-volume-copy-cache-and-hardlink-byte-equivalence',
                    protocol=PROTOCOL, source=str(source), local_source=str(local_source), sha256=checksum,
                    source_device=source.stat().st_dev, local_device=linked.stat().st_dev,
                    ordinary_copy_file_id=ordinary.stat().st_ino, local_hardlink_file_id=linked.stat().st_ino,
                    canonical_source_file_id=source.stat().st_ino)
