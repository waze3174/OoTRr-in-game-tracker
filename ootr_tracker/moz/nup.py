# Copied from Mozencaz/OotrR (MIT, Copyright (c) 2026 Mozencaz), v0.8.0 (eb66827): src/oot_rando/formats/inspect_nup.py (the container reader; its command line left out).
# The notice is in THIRD_PARTY_NOTICES.md.
"""Read-only NUP inspection helper; never modifies the game container."""
import hashlib
import struct
from pathlib import Path


class Nup:
    def __init__(self, path):
        self.path = Path(path)
        self.stream = self.path.open('rb')
        head = self.stream.read(128)
        if head[:4] != b'NUP\x01':
            raise ValueError('Not a NUP container')
        offset, size = struct.unpack_from('<QQ', head, 8)
        self.stream.seek(offset)
        toc = self.stream.read(size)
        if hashlib.sha256(toc).digest() != head[24:56]:
            raise ValueError('Invalid TOC hash')
        magic, pc, dc, fc, pool, plen, _ = struct.unpack_from('<IIQQQQQ', toc)
        if magic != 0x01434f54:
            raise ValueError('Invalid TOC')
        self.packages = [struct.unpack_from('<QIIII', toc, 48 + i*64) for i in range(pc)]
        pos = 48 + pc*64
        dirs = [struct.unpack_from('<IIIIQ', toc, pos+i*24) for i in range(dc)]
        pos += dc*24
        files = [struct.unpack_from('<IIQQQ32sB', toc, pos+i*80) for i in range(fc)]
        pos += fc*80
        children = struct.unpack_from('<' + 'I'*((pool-pos)//4), toc, pos)
        def name(o, n):
            return toc[pool+o:pool+o+n].decode('utf-8')
        self.entries = {}
        def walk(idx, prefix):
            o, n, first, count, _ = dirs[idx]
            for child in children[first:first+count]:
                if child < dc:
                    d = dirs[child]
                    walk(child, prefix + name(d[0], d[1]) + '/')
                else:
                    f = files[child-dc]
                    self.entries[prefix+name(f[0], f[1])] = f
        # Members are keyed by the package's rank in title-id order, not its position in
        # the TOC: the base game ('0/') always sorts before its update ('1/', title + 0x800)
        # and DLC, whatever order the dumping tool wrote them in.
        for i, p in enumerate(sorted(self.packages, key=lambda p: p[0])):
            walk(p[1], f'{i}/')

    def latest(self, path):
        """Member of ``path`` (``romfs/...``, ``exefs/...``) as the game runs it: the update's
        copy when there is one, else the base's (a dump with the update merged in has only ``0/``)."""
        for prefix in ('1/', '0/'):
            if prefix + path in self.entries:
                return prefix + path
        raise KeyError(path)

    def read(self, path):
        _, _, size, offset, extent, digest, codec = self.entries[path]
        self.stream.seek(offset)
        data = self.stream.read(extent)
        if codec == 1:
            import zstandard
            data = zstandard.ZstdDecompressor().decompress(data, max_output_size=size)
        elif codec != 0:
            raise ValueError('Unknown NUP codec')
        if len(data) != size or hashlib.sha256(data).digest() != digest:
            raise ValueError('Invalid member hash: ' + path)
        return data
