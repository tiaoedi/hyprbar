"""Icon themes only: bounded installation; no scripts or desktop reloads."""
from __future__ import annotations
import configparser
import ctypes
import errno
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import stat
import tempfile
import installer

_RESOLVE_BENEATH = 0x08
_RESOLVE_NO_MAGICLINKS = 0x02
MAX_ENTRIES_PER_DIRECTORY = 256
MAX_ROOT_ENTRIES_PER_DIRECTORY = 256

# Release packages verified by downloading and installing in isolated scratch.
FAMILIES = {
    'Zafiro': 'zayronxio/Zafiro-icons',
    'Frost': 'thissayantan/frost-icon-theme',
    'Full Icon Themes': 'niraletter/full-icon-themes',
}


def discover(roots: list[Path] | None = None) -> list[Theme]:
    if roots is None:
        roots = [Path.home()/'.icons', Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'icons']
        roots += [Path(p)/'icons' for p in os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if p]
    found = {}
    for root in roots:
        root_fd = None
        try:
            root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        except OSError:
            continue
        try:
            names = []
            try:
                with os.scandir(root_fd) as entries:
                    iterator = iter(entries)
                    examined = 0
                    while examined < MAX_ROOT_ENTRIES_PER_DIRECTORY:
                        try:
                            entry = next(iterator)
                        except StopIteration:
                            break
                        examined += 1
                        try:
                            if entry.name.startswith('.') or entry.name in found or not entry.is_dir(follow_symlinks=False):
                                continue
                        except OSError:
                            continue
                        names.append(entry.name)
            except OSError:
                continue
            for name in sorted(names):
                if name in found:
                    continue
                try:
                    theme_fd = _open_relative(
                        root_fd, name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
                except OSError:
                    continue
                try:
                    found[name] = _read_theme(root/name, audit_links=False, root_fd=theme_fd)
                except (ValueError, OSError):
                    continue
                finally:
                    os.close(theme_fd)
        finally:
            os.close(root_fd)
    return sorted(found.values(), key=lambda t:t.name.casefold())


def preview(path: Path, side: int = 96, *, root: Path | None = None,
            root_identity: tuple[int, int] | None = None):
    """Raster pixels, including bounded SVG through system librsvg (no scripts)."""
    import io
    from PIL import Image
    path = Path(path)
    if not 1 <= side <= 256:
        raise ValueError('Limites da prévia excedidos')
    if root is None:
        with path.open('rb') as stream:
            if os.fstat(stream.fileno()).st_size > installer.MAX_FILE:
                raise ValueError('Limites da prévia excedidos')
            data = stream.read(installer.MAX_FILE+1)
    else:
        root = Path(root)
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            identity = os.fstat(root_fd)
            if root_identity is not None and (identity.st_dev, identity.st_ino) != root_identity:
                raise ValueError('O tema mudou desde a listagem; atualize a lista antes da prévia')
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError as exc:
                raise ValueError('A prévia está fora do tema selecionado') from exc
            fd = _open_relative(root_fd, relative, os.O_RDONLY | os.O_CLOEXEC)
            with os.fdopen(fd, 'rb') as stream:
                if os.fstat(stream.fileno()).st_size > installer.MAX_FILE:
                    raise ValueError('Limites da prévia excedidos')
                data = stream.read(installer.MAX_FILE+1)
        finally:
            os.close(root_fd)
    if len(data) > installer.MAX_FILE:
        raise ValueError('Limites da prévia excedidos')
    if path.suffix.lower() != '.svg':
        with Image.open(io.BytesIO(data)) as image:
            if image.width*image.height > 16_000_000: raise ValueError('Imagem grande demais')
            image = image.convert('RGBA')
            image.thumbnail((side, side), Image.Resampling.LANCZOS)
            canvas = Image.new('RGBA', (side, side))
            canvas.alpha_composite(image, ((side-image.width)//2, (side-image.height)//2))
            return canvas
    import ctypes.util
    import re
    import xml.etree.ElementTree as ET
    try: tree = ET.fromstring(data)
    except ET.ParseError as exc: raise ValueError('SVG inválido') from exc
    if tree.tag not in ('svg', '{http://www.w3.org/2000/svg}svg'):
        raise ValueError('Não é SVG')
    if re.search(rb'<!DOCTYPE|<!ENTITY|@import|<script|<foreignObject', data, re.I):
        raise ValueError('Conteúdo ativo ou externo recusado na prévia SVG')
    for node in tree.iter():
        for key, value in node.attrib.items():
            if key.rsplit('}',1)[-1] == 'href' and not value.startswith('#'):
                raise ValueError('Referência externa recusada na prévia SVG')
        text = ' '.join(node.attrib.values())+' '+(node.text or '')
        for reference in re.findall(r'url\(\s*([^)]*)\)', text, re.I):
            if not reference.strip(" '\"").startswith('#'):
                raise ValueError('Referência externa recusada na prévia SVG')
    rsvg_path = ctypes.util.find_library('rsvg-2'); cairo_path = ctypes.util.find_library('cairo')
    if not rsvg_path or not cairo_path: raise ValueError('Prévia SVG requer librsvg e Cairo do sistema; PNG continua disponível')
    rsvg = ctypes.CDLL(rsvg_path); cairo = ctypes.CDLL(cairo_path)
    gobject = ctypes.CDLL(ctypes.util.find_library('gobject-2.0'))
    glib = ctypes.CDLL(ctypes.util.find_library('glib-2.0'))
    void = ctypes.c_void_p
    rsvg.rsvg_handle_new_from_data.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(void)]; rsvg.rsvg_handle_new_from_data.restype = void
    class Rect(ctypes.Structure): _fields_ = [('x',ctypes.c_double),('y',ctypes.c_double),('width',ctypes.c_double),('height',ctypes.c_double)]
    rsvg.rsvg_handle_render_document.argtypes = [void, void, ctypes.POINTER(Rect), ctypes.POINTER(void)]; rsvg.rsvg_handle_render_document.restype = ctypes.c_int
    cairo.cairo_image_surface_create.argtypes = [ctypes.c_int,ctypes.c_int,ctypes.c_int]; cairo.cairo_image_surface_create.restype = void
    cairo.cairo_create.argtypes = [void]; cairo.cairo_create.restype = void
    cairo.cairo_destroy.argtypes = [void]; cairo.cairo_surface_destroy.argtypes = [void]
    gobject.g_object_unref.argtypes = [void]; glib.g_error_free.argtypes = [void]
    callback_type = ctypes.CFUNCTYPE(ctypes.c_int, void, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_uint)
    cairo.cairo_surface_write_to_png_stream.argtypes = [void, callback_type, void]; cairo.cairo_surface_write_to_png_stream.restype = ctypes.c_int
    error = void(); handle = rsvg.rsvg_handle_new_from_data(data,len(data),ctypes.byref(error))
    if error.value: glib.g_error_free(error); error = void()
    if not handle: raise ValueError('SVG não pôde ser carregado')
    surface = cairo.cairo_image_surface_create(0,side,side); context = cairo.cairo_create(surface)
    chunks = []
    @callback_type
    def collect(_closure, pointer, length):
        chunks.append(ctypes.string_at(pointer,length)); return 0
    try:
        if not rsvg.rsvg_handle_render_document(handle,context,ctypes.byref(Rect(0,0,side,side)),ctypes.byref(error)):
            raise ValueError('SVG não pôde ser renderizado')
        if cairo.cairo_surface_write_to_png_stream(surface,collect,None): raise ValueError('Falha na rasterização SVG')
        with Image.open(io.BytesIO(b''.join(chunks))) as image: return image.convert('RGBA')
    finally:
        if error.value: glib.g_error_free(error)
        cairo.cairo_destroy(context); cairo.cairo_surface_destroy(surface); gobject.g_object_unref(handle)


def install_asset(asset, destination: Path, *, opener=None, scratch: Path | None = None) -> list[Path]:
    """Reuse the cursor catalog's URL, redirect, size and digest trust boundary."""
    import online
    import hashlib
    from urllib.request import Request
    online.validate_asset(asset)
    with tempfile.TemporaryDirectory(prefix='icon-download-', dir=scratch or os.environ.get('TMPDIR')) as temporary:
        package = Path(temporary)/asset.name
        digest = hashlib.sha256(); total = 0
        with online.response_for(Request(asset.url,headers={'User-Agent':'hrprbar-install-cursor'}),asset.repo,opener) as response, package.open('wb') as stream:
            length = response.headers.get('Content-Length')
            if length is not None and (not length.isdigit() or int(length) > online.MAX_DOWNLOAD):
                raise ValueError('Tamanho HTTP inválido ou excede 64 MiB')
            while chunk := response.read(65536):
                total += len(chunk)
                if total > online.MAX_DOWNLOAD: raise ValueError('Pacote excede 64 MiB')
                digest.update(chunk); stream.write(chunk)
        if total != asset.size: raise ValueError('Download incompleto: tamanho diferente do catálogo')
        if asset.digest and asset.digest != 'sha256:'+digest.hexdigest(): raise ValueError('SHA256 não confere')
        return install(package,destination)


@dataclass(frozen=True)
class Theme:
    name: str
    path: Path
    label: str
    samples: tuple[Path, ...]
    root_identity: tuple[int, int] = (0, 0)


def validate_theme(path: Path) -> Theme:
    """Complete audit, required before installing or applying a theme."""
    return _read_theme(path, audit_links=True)


class _OpenHow(ctypes.Structure):
    _fields_ = [('flags', ctypes.c_uint64), ('mode', ctypes.c_uint64), ('resolve', ctypes.c_uint64)]


_LIBC = ctypes.CDLL(None, use_errno=True)
try:
    _OPENAT2 = _LIBC.openat2
except AttributeError:
    _OPENAT2 = None
if _OPENAT2 is not None:
    _OPENAT2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.POINTER(_OpenHow), ctypes.c_size_t]
    _OPENAT2.restype = ctypes.c_int


def _open_relative(root_fd: int, relative: str, flags: int,
                   resolve: int = _RESOLVE_BENEATH | _RESOLVE_NO_MAGICLINKS) -> int:
    if _OPENAT2 is None:
        raise OSError('openat2 indisponível; leitura segura recusada')
    how = _OpenHow(flags, 0, resolve)
    fd = _OPENAT2(root_fd, os.fsencode(relative), ctypes.byref(how), ctypes.sizeof(how))
    if fd < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), relative)
    return fd


def _audit_links(root_fd: int) -> None:
    """Audit every link fd-relatively; internal relative links remain valid."""
    pending = [('', os.dup(root_fd))]
    try:
        while pending:
            parent, directory_fd = pending.pop()
            try:
                with os.scandir(directory_fd) as entries:
                    for entry in entries:
                        relative = f'{parent}/{entry.name}' if parent else entry.name
                        info = os.stat(entry.name, dir_fd=directory_fd, follow_symlinks=False)
                        entry_fd = os.open(
                            entry.name, getattr(os, 'O_PATH', os.O_RDONLY) | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=directory_fd)
                        opened = os.fstat(entry_fd)
                        if (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)) != (
                                opened.st_dev, opened.st_ino, stat.S_IFMT(opened.st_mode)):
                            os.close(entry_fd)
                            raise ValueError('Entrada mudou durante a auditoria: '+relative)
                        if stat.S_ISLNK(opened.st_mode):
                            os.close(entry_fd)
                            target_fd = _open_relative(
                                root_fd, relative, getattr(os, 'O_PATH', os.O_RDONLY) | os.O_CLOEXEC)
                            os.close(target_fd)
                        elif stat.S_ISDIR(opened.st_mode):
                            os.close(entry_fd)
                            child_fd = os.open(
                                entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                dir_fd=directory_fd)
                            child_stat = os.fstat(child_fd)
                            if (opened.st_dev, opened.st_ino) != (child_stat.st_dev, child_stat.st_ino):
                                os.close(child_fd)
                                raise ValueError('Diretório mudou durante a auditoria: '+relative)
                            pending.append((relative, child_fd))
                        else:
                            os.close(entry_fd)
            finally:
                os.close(directory_fd)
    finally:
        for _, directory_fd in pending:
            os.close(directory_fd)


def _read_theme(path: Path, *, audit_links: bool, root_fd: int | None = None) -> Theme:
    """Read metadata/samples; listing does not traverse the entire icon tree."""
    from PIL import Image
    import xml.etree.ElementTree as ET
    path = Path(path)
    theme_name = path.name
    owns_root_fd = root_fd is None
    try:
        if root_fd is None:
            root_fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        root_stat = os.fstat(root_fd)
        base = Path(os.readlink(f'/proc/self/fd/{root_fd}'))
        metadata_fd = _open_relative(root_fd, 'index.theme', os.O_RDONLY | os.O_CLOEXEC)
        with os.fdopen(metadata_fd, 'rb') as stream:
            if os.fstat(stream.fileno()).st_size > 1024*1024:
                raise ValueError('index.theme grande demais')
            metadata_text = stream.read(1024*1024+1)
        if len(metadata_text) > 1024*1024:
            raise ValueError('index.theme grande demais')
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(metadata_text.decode('utf-8'))
        section = parser['Icon Theme']
        directories = [d.strip() for d in section['Directories'].split(',') if d.strip()]
        directories += [d.strip() for d in section.get('ScaledDirectories', '').split(',') if d.strip()]
        if not directories or not section.get('Name', '').strip():
            raise ValueError('Nome ou diretórios ausentes')
        if audit_links:
            _audit_links(root_fd)
        samples = []
        for directory in dict.fromkeys(directories):
            rel = installer.safe_name(directory)
            if rel == Path('.'):
                raise ValueError('Diretório escapa do tema')
            details = parser[directory]
            if int(details['Size']) <= 0 or details.get('Type', 'Threshold') not in ('Fixed', 'Scalable', 'Threshold'):
                raise ValueError('Metadados de diretório inválidos')
            folder_fd = _open_relative(
                root_fd, rel.as_posix(), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            if len(samples) >= 12:
                os.close(folder_fd)
                continue
            try:
                with os.scandir(folder_fd) as entries:
                    examined = 0
                    iterator = iter(entries)
                    while len(samples) < 12 and examined < MAX_ENTRIES_PER_DIRECTORY:
                        try:
                            entry = next(iterator)
                        except StopIteration:
                            break
                        examined += 1
                        suffix = Path(entry.name).suffix.lower()
                        if suffix not in ('.png', '.svg', '.xpm'):
                            continue
                        sample_relative = (rel/entry.name).as_posix()
                        sample_path = base/rel/entry.name
                        try:
                            sample_fd = _open_relative(root_fd, sample_relative, os.O_RDONLY | os.O_CLOEXEC)
                        except OSError as exc:
                            if exc.errno == errno.EXDEV:
                                raise ValueError('Imagem escapa do tema: '+sample_relative) from exc
                            continue
                        try:
                            with os.fdopen(sample_fd, 'rb') as stream:
                                file_stat = os.fstat(stream.fileno())
                                if not stat.S_ISREG(file_stat.st_mode):
                                    continue
                                if suffix == '.svg':
                                    if file_stat.st_size > installer.MAX_FILE:
                                        continue
                                    tree = ET.fromstring(stream.read())
                                    if tree.tag not in ('svg', '{http://www.w3.org/2000/svg}svg'):
                                        continue
                                else:
                                    with Image.open(stream) as image:
                                        if image.width*image.height > 16_000_000:
                                            continue
                                        image.verify()
                            samples.append(sample_path)
                        except (OSError, ValueError, ET.ParseError):
                            continue
            finally:
                os.close(folder_fd)
        if not samples:
            raise ValueError('Tema sem imagens de ícones válidas')
        return Theme(theme_name, base, section['Name'], tuple(samples),
                     (root_stat.st_dev, root_stat.st_ino))
    except (KeyError, configparser.Error, OSError, RuntimeError) as exc:
        raise ValueError('Tema de ícones inválido: '+str(exc)) from exc
    finally:
        if owns_root_fd and root_fd is not None:
            os.close(root_fd)


def install(source: Path, destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.icon-stage-', dir=destination) as temporary:
        payload = Path(temporary)/'payload'; payload.mkdir()
        installer.unpack(source, payload)
        roots = [p.parent for p in payload.rglob('index.theme') if not p.is_symlink()]
        if not roots:
            raise ValueError('Nenhum index.theme de ícones encontrado')
        package_name = source.name
        for suffix in ('.tar.gz','.tar.xz','.tar.bz2','.tar.zst','.tgz','.txz','.tbz2','.zip','.tar'):
            if package_name.lower().endswith(suffix):
                package_name = package_name[:-len(suffix)]; break
        if not package_name or package_name.startswith('.'):
            raise ValueError('Nome de pacote inválido')
        names = [package_name if p == payload else p.name for p in roots]
        if len(set(names)) != len(names):
            raise ValueError('Nomes duplicados')
        for root, name in zip(roots, names):
            validate_theme(root)
            if os.path.lexists(destination/name):
                raise FileExistsError('Tema já instalado: '+name)
        libc = ctypes.CDLL(None, use_errno=True)
        rename = libc.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        installed = []
        try:
            for root, name in zip(roots, names):
                target = destination/name
                if rename(-100, os.fsencode(root), -100, os.fsencode(target), 1):
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err), str(target))
                installed.append(target)
        except Exception:
            for path in installed:
                shutil.rmtree(path)
            raise
        return installed


def apply(theme: Theme, *, home: Path | None = None, runner=None) -> str:
    """Explicit GTK3/4 + GSettings icon-only transaction, with exact-target backups."""
    import io
    import json
    import re
    import uuid
    import ast
    import settings
    if home is not None and runner is None:
        raise ValueError('Home isolado exige runner injetado; GSettings real proibido')
    if not re.fullmatch(r'[\w .+()@-]+', theme.name):
        raise ValueError('Nome de tema não suportado')
    validated = validate_theme(theme.path)
    if theme.root_identity != (0, 0) and validated.root_identity != theme.root_identity:
        raise ValueError('O tema mudou desde a listagem; atualize a lista antes de aplicar')
    execute = runner or settings.run
    cfg = home/'.config' if home is not None else Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))
    command = ['gsettings', 'get', 'org.gnome.desktop.interface', 'icon-theme']
    ok, previous = execute(command)
    if not ok:
        raise RuntimeError('Não foi possível ler GSettings antes da alteração: '+previous)
    # Parse a GVariant string, never shell-evaluate it.
    try:
        previous_value = ast.literal_eval(previous)
        if not isinstance(previous_value, str): raise ValueError('não é string')
    except (ValueError, SyntaxError) as exc:
        raise RuntimeError('GSettings devolveu um valor inválido') from exc
    token = uuid.uuid4().hex
    changes = {}; aliases = {}
    for version in ('3.0', '4.0'):
        alias = cfg/f'gtk-{version}/settings.ini'
        if alias.is_symlink() and not alias.exists():
            raise ValueError('settings.ini contém link quebrado')
        target = alias.resolve()
        aliases[str(alias)] = {'target': str(target), 'link': os.readlink(alias) if alias.is_symlink() else None}
        parser = configparser.ConfigParser(interpolation=None); parser.optionxform = str
        if target.exists(): parser.read_string(target.read_text())
        if not parser.has_section('Settings'): parser.add_section('Settings')
        parser['Settings']['gtk-icon-theme-name'] = theme.name
        out = io.StringIO(); parser.write(out)
        changes[target] = out.getvalue()
    journal = cfg/'hrprbar-install-cursor/icon-backups'/token
    journal.mkdir(parents=True, mode=0o700)
    snapshot = {'gsettings_icon_theme': previous, 'paths': aliases}
    (journal/'snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    written = []; changed_gsettings = False
    def atomic(target: Path, data: bytes, mode: int = 0o600) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.icons-', dir=target.parent)
        try:
            with os.fdopen(fd, 'wb') as stream: stream.write(data)
            os.chmod(name, mode)
            os.replace(name, target)
        finally:
            if os.path.exists(name): os.unlink(name)
    try:
        for target, text in changes.items():
            old = target.read_bytes() if target.exists() else None
            mode = target.stat().st_mode & 0o777 if target.exists() else 0o600
            if old is not None:
                shutil.copy2(target, target.with_name(target.name+'.bak-'+token))
            atomic(target, text.encode(), mode)
            written.append((target, old, mode))
            if target.read_text() != text: raise RuntimeError('Falha de verificação GTK')
        changed_gsettings = True
        ok, output = execute(['gsettings', 'set', 'org.gnome.desktop.interface', 'icon-theme', json.dumps(theme.name, ensure_ascii=False)])
        if not ok: raise RuntimeError('Falha GSettings: '+output)
        ok, output = execute(command)
        try: valid = ast.literal_eval(output) == theme.name
        except (ValueError, SyntaxError): valid = False
        if not ok or not valid: raise RuntimeError('Falha de verificação GSettings icon-theme: '+output)
    except Exception as exc:
        failures = []
        for target, old, mode in reversed(written):
            try:
                if old is None: target.unlink(missing_ok=True)
                else: atomic(target, old, mode)
            except OSError as rollback: failures.append(str(rollback))
        if changed_gsettings:
            ok, output = execute(['gsettings', 'set', 'org.gnome.desktop.interface', 'icon-theme', previous])
            if not ok: failures.append('GSettings: '+output)
            ok, output = execute(command)
            try: restored = ast.literal_eval(output) == previous_value
            except (ValueError, SyntaxError): restored = False
            if not ok or not restored: failures.append('GSettings anterior não confirmado: '+output)
        raise RuntimeError(str(exc)+'; backup: '+str(journal)+('; restauração falhou: '+'; '.join(failures) if failures else '; valores anteriores restaurados')) from exc
    return ('VERIFICADO: GTK3/4 e GSettings icon-theme = '+theme.name+'\nBackup: '+str(journal)+'\nSomente ícones alterados. Cursores, compositor e barra não foram modificados. Nenhum aplicativo reiniciado. Aplicativos em execução, Qt e sandboxes podem manter caches ou configurações próprias.')
