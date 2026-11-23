"""Reading and writing the running game's memory in an emulator process (Windows and Linux).

Copied from Mozencaz/OotrR (MIT, Copyright (c) 2026 Mozencaz), v0.8.0 (eb66827), src/oot_rando/tracker/live_memory.py,
cut to what the console's bridge needs: finding the emulator that has the game loaded and reading and writing its
guest memory. The recomps (Hookshot, Longshot) and the GameData readers are left out.

Emulators (Eden, Ryuchii, yuzu and forks) map the guest's memory as a window of their own process: host = base + guest.
The main module is loaded at a random page near 0x80000000 at every boot; ``emulator_layout`` finds the modules by
their MOD0 header in the process and keeps the guest address where the GameData slot leads to a table holding a known
key.
"""
import bisect
import ctypes
import os
import struct
import sys
import time
from pathlib import Path, PureWindowsPath

HOST_BASE = 0x100000000000


GAMEDATA_SLOT = 0x84C9E180
MAX_TABLE = 1 << 20
SEQUENCE_IS_CHILDHOOD = 0xCEA220D3   # murmur3('Sequence_IsChildhood'), always present


EMULATOR_EXES = {'lichii.exe', 'ryuchii.exe', 'eden.exe', 'yuzu.exe', 'suyu.exe', 'citron.exe', 'sudachi.exe'}


def parse_exe_names(text):
    """Executable names from a free list (commas, semicolons or lines): lower case, '.exe' added."""
    names = set()
    for part in text.replace(';', ',').replace('\n', ',').split(','):
        name = PureWindowsPath(part.strip().strip('"')).name.lower()
        if name:
            names.add(name if name.endswith('.exe') else name + '.exe')
    return names


_extra_emulators = set()   # executables the player listed, besides the known ones


def set_extra_emulators(text):
    """Executables the player listed (``--emulator``), used by the next process scan."""
    global _extra_emulators
    _extra_emulators = parse_exe_names(text or '')


def emulator_exes():
    """Known yuzu-family executables plus the ones the player listed."""
    return EMULATOR_EXES | _extra_emulators


def plain_name(name):
    """Executable name without folder and '.exe', lower case: 'ryuchii.exe' matches the Linux 'ryuchii'."""
    name = PureWindowsPath(str(name).strip().strip('"')).name.lower()
    return name[:-4] if name.endswith('.exe') else name


HOOKSHOT_MAIN = 0x80020000                 # main's address the GameData slot's offset is counted from
MEM_COMMIT = 0x1000


MAX_MODULE = 0x10000000                              # MOD0 may sit past the first region (main: +0x3c4705c)
GUEST_CODE = range(0x80000000, 0x84000000, 0x1000)   # where emulators load the main module


class LiveUnavailable(Exception):
    pass


def valid_slot(read, slot):
    """True when guest ``slot`` leads to a GameData manager whose table knows a vanilla key.

    ``read(guest, size)`` returns bytes or None. Pure: tested without a game.
    """
    def pointer(address):
        raw = read(address, 8)
        value = struct.unpack('<Q', raw)[0] if raw else 0
        return value if 0x10000 <= value < 1 << 48 and not value & 7 else 0

    holder = pointer(slot)
    manager = pointer(holder) if holder else 0
    header = read(manager, 48) if manager else None
    if not header:
        return False
    count, size = struct.unpack_from('<I', header, 16)[0], struct.unpack_from('<I', header, 44)[0]
    entries, table = struct.unpack_from('<QQ', header, 24)
    if not (table and entries and 0 < size <= MAX_TABLE and 0 < count <= MAX_TABLE):
        return False
    raw = read(table, size * 8)
    index = bool_slot(raw, size, SEQUENCE_IS_CHILDHOOD) if raw else None
    return index is not None and index < count


def module_starts(regions, read):
    """Host addresses of the loaded NSO modules (committed regions starting with a MOD0 pointer)."""
    result = []
    for address, size, state in regions:
        if state != MEM_COMMIT or size < 0x1000:
            continue
        head = read(address, 8)
        offset = struct.unpack_from('<I', head, 4)[0] if head else 0
        if 8 <= offset < MAX_MODULE and not offset & 3 and read(address + offset, 4) == b'MOD0':
            result.append(address)
    return result


def emulator_layout(regions, read):
    """(host base of guest memory, guest GameData slot) in an emulator process, or None.

    ``regions``: (address, size, state) of the process, in address order; ``read(host, size)``
    returns bytes or None. Pure: tested without a game.
    """
    offset = GAMEDATA_SLOT - HOOKSHOT_MAIN
    for module in module_starts(regions, read):
        raw = read(module + offset, 8)
        if not raw or not struct.unpack('<Q', raw)[0]:
            continue   # not main, or the game has not loaded its data yet
        for guest in GUEST_CODE:
            base = module - guest
            if valid_slot(lambda address, length: read(base + address, length), guest + offset):
                return base, guest + offset
    return None


class MemoryRegion(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_ulonglong), ('AllocationBase', ctypes.c_ulonglong),
                ('AllocationProtect', ctypes.c_ulong), ('PartitionId', ctypes.c_ushort),
                ('RegionSize', ctypes.c_ulonglong), ('State', ctypes.c_ulong),
                ('Protect', ctypes.c_ulong), ('Type', ctypes.c_ulong)]


class ProcessMemory:
    """ReadProcessMemory on an emulator that has the game loaded.

    ``base``: host address of guest address 0; ``slot``: guest address of the GameData slot.
    """
    def __init__(self):
        from ctypes import wintypes
        self.wt = wintypes
        self.k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.k32.OpenProcess.restype = wintypes.HANDLE
        self.k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                               ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self.k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_ulonglong, ctypes.POINTER(MemoryRegion),
                                            ctypes.c_size_t]
        self.k32.VirtualQueryEx.restype = ctypes.c_size_t
        self.handle, self.pid, self.next_scan = None, None, 0.0
        self.image = ''   # full path of the attached game's exe
        self.base, self.slot = HOST_BASE, GAMEDATA_SLOT

    def _pids(self):
        from ctypes import wintypes
        psapi = ctypes.WinDLL('psapi')
        array = (wintypes.DWORD * 4096)()
        needed = wintypes.DWORD()
        psapi.EnumProcesses(array, ctypes.sizeof(array), ctypes.byref(needed))
        return list(array[:needed.value // 4])

    def _exe(self, handle):
        size = self.wt.DWORD(520)
        buffer = ctypes.create_unicode_buffer(size.value)
        if self.k32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
        return ''

    def attach(self):
        if self.handle:
            code = self.wt.DWORD()
            if self.k32.GetExitCodeProcess(self.handle, ctypes.byref(code)) and code.value == 259:  # STILL_ACTIVE
                return
            self.close()
        now = time.monotonic()
        if now < self.next_scan:
            raise LiveUnavailable('game not running')
        self.next_scan = now + 5   # scanning every process each second would be wasteful
        emulators = emulator_exes()
        for pid in self._pids():
            handle = self.k32.OpenProcess(0x0010 | 0x0400, False, pid)   # VM_READ | QUERY_INFORMATION
            if not handle:
                continue
            image = self._exe(handle)
            name = Path(image).name.lower()
            layout = None
            if name in emulators:
                layout = emulator_layout(self._regions(handle), lambda host, size: self._read(handle, host, size))
            if layout:
                self.handle, self.pid, self.image = handle, pid, image
                self.base, self.slot = layout
                return
            self.k32.CloseHandle(handle)
        raise LiveUnavailable('game not running')

    def _regions(self, handle):
        """(address, size, state) of every region of the process, in address order."""
        result, address, region = [], 0, MemoryRegion()
        while self.k32.VirtualQueryEx(handle, address, ctypes.byref(region), ctypes.sizeof(region)):
            result.append((region.BaseAddress, region.RegionSize, region.State))
            address = region.BaseAddress + region.RegionSize
        return result

    def _read(self, handle, host, size):
        buffer, done = ctypes.create_string_buffer(size), ctypes.c_size_t()
        if not self.k32.ReadProcessMemory(handle, ctypes.c_void_p(host), buffer, size, ctypes.byref(done)) \
                or done.value != size:
            return None
        return buffer.raw

    def read(self, guest, size):
        data = self._read(self.handle, self.base + guest, size)
        if data is None:
            raise LiveUnavailable(f'cannot read at {guest:#x}')
        return data

    def write(self, guest, data):
        """WriteProcessMemory through a handle opened for this write only."""
        handle = self.k32.OpenProcess(0x0008 | 0x0020 | 0x0010, False, self.pid)   # VM_OPERATION|VM_WRITE|VM_READ
        if not handle:
            raise LiveUnavailable('cannot open the game for writing')
        try:
            self.k32.WriteProcessMemory.argtypes = [self.wt.HANDLE, ctypes.c_void_p, ctypes.c_char_p,
                                                    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
            done = ctypes.c_size_t()
            if not self.k32.WriteProcessMemory(handle, ctypes.c_void_p(self.base + guest), data, len(data),
                                               ctypes.byref(done)) or done.value != len(data):
                raise LiveUnavailable(f'cannot write at {guest:#x}')
        finally:
            self.k32.CloseHandle(handle)

    def close(self):
        if self.handle:
            self.k32.CloseHandle(self.handle)
        self.handle, self.pid, self.image = None, None, ''


# /proc/<pid>/maps rows never read: kernel pages /proc/<pid>/mem refuses, and device mappings
# (GPU memory). Guest memory is the emulator's memfd ("/memfd:HostMemory") or anonymous.
SKIPPED_MAPPINGS = ('[vvar]', '[vvar_vclock]', '[vsyscall]')
COMM_LENGTH = 15   # /proc/<pid>/comm keeps the first 15 bytes of the name


def parse_maps(text):
    """(start, size, permissions, path) of each /proc/<pid>/maps row (pure)."""
    rows = []
    for line in text.splitlines():
        fields = line.split(None, 5)
        if len(fields) < 5 or '-' not in fields[0]:
            continue
        try:
            start, end = (int(value, 16) for value in fields[0].split('-', 1))
        except ValueError:
            continue
        rows.append((start, end - start, fields[1], fields[5].strip() if len(fields) > 5 else ''))
    return rows


def readable_regions(rows):
    """(address, size, MEM_COMMIT) of the readable mappings, as :func:`emulator_layout` takes them (pure)."""
    return [(start, size, MEM_COMMIT) for start, size, permissions, path in rows
            if permissions.startswith('r') and path not in SKIPPED_MAPPINGS
            and not (path.startswith('/dev/') and not path.startswith('/dev/shm/'))]


MEMFD_NAME = '/memfd:HostMemory'   # the yuzu-family emulators' guest memory file (memfd_create)


def is_guest_memfd(path):
    """True for the link name or maps path of a guest memory file: an emulator's (pure)."""
    if path.endswith(' (deleted)'):
        path = path[:-len(' (deleted)')]
    return path == MEMFD_NAME


def memfd_mappings(text):
    """(start, size, file offset, inode) of each /proc/<pid>/maps row of a guest memory file,
    whatever its protection (pure)."""
    rows = []
    for line in text.splitlines():
        fields = line.split(None, 5)
        if len(fields) < 6 or not is_guest_memfd(fields[5].strip()):
            continue
        try:
            start, end = (int(value, 16) for value in fields[0].split('-', 1))
            rows.append((start, end - start, int(fields[2], 16), int(fields[4])))
        except ValueError:
            continue
    return rows


class MemfdWindows:
    """Host addresses to offsets in the guest memory file, from its mappings (pure).

    Mappings that continue each other in both the address space and the file are joined; the
    emulator changes page protections often, never which file page an address shows.
    """
    def __init__(self, mappings):
        self.windows = []
        for start, size, offset, _ in sorted(mappings):
            last = self.windows[-1] if self.windows else None
            if last and last[0] + last[1] == start and last[2] + last[1] == offset:
                self.windows[-1] = (last[0], last[1] + size, last[2])
            else:
                self.windows.append((start, size, offset))
        self.starts = [window[0] for window in self.windows]

    def pieces(self, host, size):
        """[(file offset, length)] covering host..host+size, or None when part of it is not in the file."""
        result = []
        while size > 0:
            index = bisect.bisect_right(self.starts, host) - 1
            if index < 0:
                return None
            start, length, offset = self.windows[index]
            if host >= start + length:
                return None
            part = min(size, start + length - host)
            result.append((offset + host - start, part))
            host, size = host + part, size - part
        return result


def exe_link_name(target):
    """Name of the /proc/<pid>/exe target; an executable replaced on disk ends in ' (deleted)' (pure)."""
    if target.endswith(' (deleted)'):
        target = target[:-len(' (deleted)')]
    return plain_name(target.replace('\\', '/').rsplit('/', 1)[-1])


def names_match(names, wanted):
    """True when a process name is a wanted emulator's (``wanted``: plain names); a 15-character
    name may be a truncated /proc/<pid>/comm (pure)."""
    return any(name and (name in wanted or (len(name) == COMM_LENGTH and any(w.startswith(name) for w in wanted)))
               for name in names)


def linux_process_names(proc, pid):
    """Plain names of a process: its comm and the file name of its executable (when readable)."""
    names = set()
    try:
        names.add(plain_name(Path(proc, str(pid), 'comm').read_text(encoding='utf-8', errors='replace').strip()))
    except OSError:
        pass
    try:
        names.add(exe_link_name(os.readlink(os.path.join(proc, str(pid), 'exe'))))
    except (OSError, NotImplementedError, ValueError):
        pass
    return names


def linux_emulator_pids(emulators, proc='/proc', own=None):
    """Process ids whose comm or executable name is one of ``emulators`` (with or without '.exe')."""
    wanted = {plain_name(name) for name in emulators}
    try:
        entries = os.listdir(proc)
    except OSError:
        return []
    pids = sorted(int(entry) for entry in entries if entry.isdigit() and int(entry) != own)
    return [pid for pid in pids if names_match(linux_process_names(proc, pid), wanted)]


def linux_exe_path(proc, pid):
    """Full path of a process's executable ('' when unreadable), without a ' (deleted)' mark."""
    try:
        target = os.readlink(os.path.join(proc, str(pid), 'exe'))
    except (OSError, NotImplementedError, ValueError):
        return ''
    return target[:-len(' (deleted)')] if target.endswith(' (deleted)') else target


def ptrace_scope(proc='/proc'):
    """Yama's kernel.yama.ptrace_scope (0 to 3), or None without Yama."""
    try:
        return int(Path(proc, 'sys', 'kernel', 'yama', 'ptrace_scope').read_text(encoding='ascii').strip())
    except (OSError, ValueError):
        return None


def denied_message(scope):
    """Why Linux refused to open the game's memory, and the fix (pure)."""
    if scope == 1:
        return ('Linux refused to read the game\'s memory: kernel.yama.ptrace_scope is 1 (only a parent '
                'process may read it). Fix: the game can allow it with prctl(PR_SET_PTRACER, '
                'PR_SET_PTRACER_ANY), or set kernel.yama.ptrace_scope to 0 (sysctl, as root).')
    if scope == 2:
        return ('Linux refused to read the game\'s memory: kernel.yama.ptrace_scope is 2 (administrators '
                'only). Fix: set kernel.yama.ptrace_scope to 0 (sysctl, as root).')
    if scope == 3:
        return ('Linux refused to read the game\'s memory: kernel.yama.ptrace_scope is 3 (no process may, '
                'and it stays so until a restart). Fix: set it to 0 in the boot settings (sysctl.d), then restart.')
    return ('Linux refused to read the game\'s memory' + (f' (kernel.yama.ptrace_scope is {scope})'
            if scope is not None else '') + ': run this application as the user who runs the game.')


class LinuxProcessMemory:
    """Memory of a native Linux emulator that has the game loaded (same interface as :class:`ProcessMemory`).

    First the emulator's guest memory file (``/memfd:HostMemory``), opened again through ``/proc/<pid>/fd`` and read at
    the offsets ``/proc/<pid>/maps`` gives: that needs only read access to the process, which
    kernel.yama.ptrace_scope 1 (SteamOS, Ubuntu) allows. Else ``/proc/<pid>/mem``, which needs ptrace access.

    Plain os.pread/os.pwrite (no libc through ctypes): the permission check happens once when the
    file is opened, and a read past the data just comes back short.
    """
    def __init__(self, proc='/proc'):
        self.proc, self.fd, self.pid, self.next_scan = proc, None, None, 0.0
        self.base, self.slot = HOST_BASE, GAMEDATA_SLOT
        self.failure = 'game not running'   # the last scan's answer, repeated until the next scan
        self.image = ''   # full path of the attached game's executable
        self.windows, self.memfd, self.inode, self.next_maps = None, None, None, 0.0   # memory file only

    def _open(self, pid, flags):
        return os.open(os.path.join(self.proc, str(pid), 'mem'), flags)

    def _maps(self, pid):
        try:
            return Path(self.proc, str(pid), 'maps').read_text(encoding='utf-8', errors='replace')
        except OSError:
            return ''

    def _regions(self, pid):
        return readable_regions(parse_maps(self._maps(pid)))

    def _guest_memfds(self, pid):
        """``/proc/<pid>/fd`` entries of the process's guest memory files, found by link name."""
        folder = os.path.join(self.proc, str(pid), 'fd')
        try:
            entries = sorted((entry for entry in os.listdir(folder) if entry.isdigit()), key=int)
        except OSError:
            return []
        paths = []
        for entry in entries:
            try:
                if is_guest_memfd(os.readlink(os.path.join(folder, entry))):
                    paths.append(os.path.join(folder, entry))
            except OSError:
                continue
        return paths

    @staticmethod
    def _read(fd, host, size):
        try:
            data = os.pread(fd, size, host)
        except (OSError, OverflowError):
            return None
        return data if len(data) == size else None

    @staticmethod
    def _read_file(fd, windows, host, size):
        pieces = windows.pieces(host, size)
        if pieces is None:
            return None
        data = b''
        for offset, length in pieces:
            try:
                part = os.pread(fd, length, offset)
            except (OSError, OverflowError):
                return None
            if len(part) != length:
                return None
            data += part
        return data

    def _attach_memfd(self, pid):
        """(fd, path, inode, windows, layout) through a guest memory file of ``pid``, or None."""
        text = self._maps(pid)
        for path in self._guest_memfds(pid):
            try:
                fd = os.open(path, os.O_RDONLY)
            except OSError:
                continue
            inode = os.fstat(fd).st_ino
            mappings = [row for row in memfd_mappings(text) if row[3] == inode]
            windows = MemfdWindows(mappings)
            regions = [(start, size, MEM_COMMIT) for start, size, _, _ in mappings]
            layout = emulator_layout(regions, lambda host, size: self._read_file(fd, windows, host, size))
            if layout:
                return fd, path, inode, windows, layout
            os.close(fd)
        return None

    def _read_attached(self, host, size):
        if self.fd is None:
            return None
        if self.windows is None:
            return self._read(self.fd, host, size)
        data = self._read_file(self.fd, self.windows, host, size)
        if data is None and time.monotonic() >= self.next_maps:
            # the game may have mapped more memory since: read the mappings again, at most once a second
            self.next_maps = time.monotonic() + 1
            self.windows = MemfdWindows([row for row in memfd_mappings(self._maps(self.pid)) if row[3] == self.inode])
            data = self._read_file(self.fd, self.windows, host, size)
        return data

    def attach(self):
        if self.fd is not None:
            if Path(self.proc, str(self.pid)).is_dir():
                return
            self.close()
        now = time.monotonic()
        if now < self.next_scan:
            raise LiveUnavailable(self.failure)
        self.next_scan = now + 5   # same pace as the Windows scan
        denied = False
        for pid in linux_emulator_pids(emulator_exes(), self.proc, os.getpid()):
            found = self._attach_memfd(pid)
            if found:
                self.fd, self.memfd, self.inode, self.windows, (self.base, self.slot) = found
                self.pid, self.image = pid, linux_exe_path(self.proc, pid)
                return
            try:
                fd = self._open(pid, os.O_RDONLY)
            except PermissionError:
                denied = True
                continue
            except OSError:
                continue
            layout = emulator_layout(self._regions(pid), lambda host, size: self._read(fd, host, size))
            if layout:
                self.fd, self.pid, self.image = fd, pid, linux_exe_path(self.proc, pid)
                self.base, self.slot = layout
                return
            os.close(fd)
        self.failure = denied_message(ptrace_scope(self.proc)) if denied else 'game not running'
        raise LiveUnavailable(self.failure)

    def read(self, guest, size):
        data = self._read_attached(self.base + guest, size)
        if data is None:
            raise LiveUnavailable(f'cannot read at {guest:#x}')
        return data

    def write(self, guest, data):
        """pwrite through a file opened for this write only."""
        if self.windows is not None:
            self._write_file(guest, data)
            return
        try:
            fd = self._open(self.pid, os.O_RDWR)
        except PermissionError:
            raise LiveUnavailable(denied_message(ptrace_scope(self.proc))) from None
        except OSError:
            raise LiveUnavailable('cannot open the game for writing') from None
        try:
            done = os.pwrite(fd, data, self.base + guest)
        except (OSError, OverflowError):
            done = -1
        finally:
            os.close(fd)
        if done != len(data):
            raise LiveUnavailable(f'cannot write at {guest:#x}')

    def _write_file(self, guest, data):
        pieces = self.windows.pieces(self.base + guest, len(data))
        if pieces is None:
            raise LiveUnavailable(f'cannot write at {guest:#x}')
        try:
            fd = os.open(self.memfd, os.O_RDWR)
        except OSError:
            raise LiveUnavailable('cannot open the game for writing') from None
        done = 0
        try:
            for offset, length in pieces:
                if os.pwrite(fd, data[done:done + length], offset) != length:
                    break
                done += length
        except (OSError, OverflowError):
            pass
        finally:
            os.close(fd)
        if done != len(data):
            raise LiveUnavailable(f'cannot write at {guest:#x}')

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
        self.fd, self.pid, self.image = None, None, ''
        self.windows, self.memfd, self.inode = None, None, None


class NoProcessMemory:
    """Systems without a memory reader: always unavailable."""
    def attach(self):
        raise LiveUnavailable('live memory reading needs Windows or Linux')

    def read(self, guest, size):
        raise LiveUnavailable('live memory reading needs Windows or Linux')

    def close(self):
        pass


def process_memory():
    """This system's process memory reader."""
    if os.name == 'nt':
        return ProcessMemory()
    if sys.platform.startswith('linux'):
        return LinuxProcessMemory()
    return NoProcessMemory()


def bool_slot(table, size, key):
    """Index of Bool ``key`` in the raw (hash, index) table, or None (pure)."""
    for probe in range(size):
        slot = (key + probe) % size
        found, index = struct.unpack_from('<II', table, slot * 8)
        if not found:
            return None
        if found == key:
            return index
    return None
