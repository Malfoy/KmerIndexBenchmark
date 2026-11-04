"""Warm only the query input, outside native timing; verify Linux page residency."""
import contextlib
import ctypes
import hashlib
import mmap
import os
from pathlib import Path
import time


@contextlib.contextmanager
def cached_query(path):
    path = Path(path)
    started = time.monotonic()
    with path.open('rb') as stream:
        size = os.fstat(stream.fileno()).st_size
        if not size:
            raise ValueError('Empty query input; no timed query may start')
        digest = hashlib.sha256()
        read_bytes = 0
        while chunk := stream.read(8 * 2**20):
            digest.update(chunk)
            read_bytes += len(chunk)
        assert read_bytes == size
        # ACCESS_COPY permits a buffer address without modifying the file or pages.
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_COPY) as mapping:
            page_size = os.sysconf('SC_PAGE_SIZE')
            pages = (size + page_size - 1) // page_size
            for offset in range(0, size, page_size):
                _ = mapping[offset]
            residency = (ctypes.c_ubyte * pages)()
            byte = ctypes.c_char.from_buffer(mapping)
            address = ctypes.addressof(byte)
            del byte
            libc = ctypes.CDLL(None, use_errno=True)
            libc.mincore.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_ubyte)]
            libc.mincore.restype = ctypes.c_int
            if libc.mincore(address, size, residency) != 0:
                error = ctypes.get_errno()
                raise OSError(error, os.strerror(error))
            resident = sum(bool(value & 1) for value in residency)
            if resident != pages:
                raise RuntimeError(f'Query input is not fully cached: {resident}/{pages} pages resident')
            yield dict(path=str(path), file_bytes=size, bytes_read_before_timing=read_bytes,
                file_sha256=digest.hexdigest(), pages=pages, resident_pages=resident,
                all_pages_resident=True, preload_seconds=time.monotonic() - started,
                cache='OS file page cache', warmup_in_native_timing=False,
                input_format='gzip FASTA' if path.suffix == '.gz' else 'FASTA',
                native_decompression_parsing_loading_output_included=True)
