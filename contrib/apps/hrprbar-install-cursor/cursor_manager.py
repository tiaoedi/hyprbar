"""Gerenciador local de temas de cursor; nenhuma alteração ao iniciar."""
from __future__ import annotations
import os
from installer import install
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Theme:
    name: str
    path: Path
    xcursor: bool
    hyprcursor: bool


def discover(roots: list[Path] | None = None) -> list[Theme]:
    if roots is None:
        home = Path.home()
        roots = [home/'.icons', Path(os.environ.get('XDG_DATA_HOME', home/'.local/share'))/'icons', home/'.local/share/icons']
        roots += [Path(p)/'icons' for p in os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':') if p]
        roots += [Path('/usr/share/icons')]
    found: dict[str, Theme] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            if path.name in found or not path.is_dir():
                continue
            x = (path/'cursors').is_dir() and any((path/'cursors').iterdir())
            h = (path/'manifest.hl').is_file()
            if x or h:
                found[path.name] = Theme(path.name, path, x, h)
    return sorted(found.values(), key=lambda t: t.name.casefold())


import ctypes as C
import ctypes.util
import struct
from PIL import Image

class XImage(C.Structure):
    _fields_ = [(n, C.c_uint32) for n in ('version','size','width','height','xhot','yhot','delay')] + [('pixels', C.POINTER(C.c_uint32))]


def available_sizes(path: Path) -> list[int]:
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('Arquivo de cursor grande demais')
    with path.open('rb') as stream:
        header = stream.read(16)
        if len(header) != 16:
            raise ValueError('Cursor inválido')
        magic, header_size, version, count = struct.unpack('<4I', header)
        if magic != 0x72756358 or count > 4096 or header_size < 16:
            raise ValueError('Cabeçalho Xcursor inválido')
        stream.seek(header_size)
        data = stream.read(count * 12)
        if len(data) != count * 12:
            raise ValueError('Tabela Xcursor truncada')
        return sorted({sub for typ,sub,pos in struct.iter_unpack('<3I',data) if typ == 0xfffd0002})


def preview(path: Path, size: int) -> tuple[Image.Image,int,list[int]]:
    sizes = available_sizes(path)
    lib = C.CDLL(ctypes.util.find_library('Xcursor') or 'libXcursor.so.1')
    lib.XcursorFilenameLoadImage.argtypes = [C.c_char_p,C.c_int]
    lib.XcursorFilenameLoadImage.restype = C.POINTER(XImage)
    lib.XcursorImageDestroy.argtypes = [C.POINTER(XImage)]
    ptr = lib.XcursorFilenameLoadImage(os.fsencode(path),int(size))
    if not ptr:
        raise ValueError('Não foi possível carregar o cursor')
    try:
        img = ptr.contents
        if not 0 < img.width <= 512 or not 0 < img.height <= 512:
            raise ValueError('Dimensões de cursor não suportadas (máximo 512)')
        rgba = bytearray()
        for p in img.pixels[:img.width * img.height]:
            a = p >> 24
            rgba.extend((min(255,((p>>16)&255)*255//a) if a else 0, min(255,((p>>8)&255)*255//a) if a else 0,min(255,(p&255)*255//a) if a else 0,a))
        return Image.frombytes('RGBA',(img.width,img.height),bytes(rgba)),img.size,sizes
    finally:
        lib.XcursorImageDestroy(ptr)
