"""Instalação local limitada, sem extractall ou substituições."""
from __future__ import annotations
import os
import shutil
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

MAX_FILES = 20000
MAX_BYTES = 256 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_RATIO = 200


def safe_name(name: str) -> Path:
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or '\x00' in name or len(name)>1024:
        raise ValueError('Caminho inseguro no pacote: '+repr(name))
    return Path(*p.parts)


def unpack(source: Path, stage: Path) -> None:
    total = count = 0
    links: list[tuple[Path,str]] = []
    seen: set[Path] = set()
    def entry(name: str, size: int, kind: str, stream=None, target: str = '') -> None:
        nonlocal total, count
        rel = safe_name(name)
        if rel == Path('.'):
            if kind == 'dir': return
            raise ValueError('Nome vazio')
        count += 1; total += size
        if count > MAX_FILES or total > MAX_BYTES or size > MAX_FILE:
            raise ValueError('Limites de segurança excedidos (20 mil arquivos / 256 MiB / 16 MiB por arquivo)')
        if rel in seen:
            raise ValueError('Entrada duplicada: '+name)
        seen.add(rel)
        dest=stage/rel
        if kind=='dir': dest.mkdir(parents=True,exist_ok=True)
        elif kind=='link':
            if len(target)>1024 or PurePosixPath(target).is_absolute() or '\\' in target:
                raise ValueError('Link inseguro')
            resolved=(dest.parent/target).resolve()
            if not resolved.is_relative_to(stage.resolve()): raise ValueError('Link fora do pacote')
            links.append((dest,target))
        elif kind=='file':
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as out:
                remaining=size
                while remaining:
                    chunk=stream.read(min(65536,remaining))
                    if not chunk: raise ValueError('Arquivo truncado')
                    out.write(chunk);remaining-=len(chunk)
        else: raise ValueError('Tipo de arquivo não permitido')
    if source.is_dir():
        if source.is_symlink(): raise ValueError('Selecione uma pasta real, não um link')
        base=source.parent
        for root,dirs,files in os.walk(source,followlinks=False):
            for name in dirs+files:
                p=Path(root)/name; info=p.lstat(); rel=p.relative_to(base).as_posix()
                if stat.S_ISLNK(info.st_mode): entry(rel,0,'link',target=os.readlink(p))
                elif stat.S_ISDIR(info.st_mode): entry(rel,0,'dir')
                elif stat.S_ISREG(info.st_mode):
                    with p.open('rb') as f: entry(rel,info.st_size,'file',f)
                else: entry(rel,0,'special')
    elif zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            for m in archive.infolist():
                if m.file_size>max(1,m.compress_size)*MAX_RATIO: raise ValueError('Taxa de compressão excessiva')
                mode=m.external_attr>>16
                if m.is_dir(): entry(m.filename,0,'dir')
                elif stat.S_ISLNK(mode):
                    if m.file_size>1024: raise ValueError('Link grande demais')
                    entry(m.filename,0,'link',target=archive.read(m).decode('utf-8'))
                elif stat.S_IFMT(mode) not in (0,stat.S_IFREG): entry(m.filename,0,'special')
                else:
                    with archive.open(m) as f: entry(m.filename,m.file_size,'file',f)
    else:
        with tarfile.open(source,'r:*') as archive:
            for m in archive:
                if m.isdir(): entry(m.name,0,'dir')
                elif m.issym(): entry(m.name,0,'link',target=m.linkname)
                elif m.isfile():
                    with archive.extractfile(m) as f: entry(m.name,m.size,'file',f)
                else: entry(m.name,0,'special')
                if total>max(1,source.stat().st_size)*MAX_RATIO: raise ValueError('Taxa de compressão excessiva')
    # Links são criados apenas depois de todos os arquivos regulares.
    for dest,target in links:
        dest.parent.mkdir(parents=True,exist_ok=True);dest.symlink_to(target)
    for dest,target in links:
        try: resolved=dest.resolve(strict=True)
        except (RuntimeError,OSError) as exc: raise ValueError('Link quebrado ou circular') from exc
        if not resolved.is_relative_to(stage.resolve()): raise ValueError('Link escapa do pacote')


def install(source: Path, destination: Path) -> list[Path]:
    from cursor_manager import preview
    destination.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.cursor-stage-',dir=destination) as tmp:
        stage=Path(tmp);payload=stage/'payload';payload.mkdir();unpack(source,payload)
        roots=[]
        for root,dirs,files in os.walk(payload,followlinks=False):
            p=Path(root)
            if (p/'cursors').is_dir() or (p/'manifest.hl').is_file():
                roots.append(p);dirs[:]=[]
        if not roots: raise ValueError('Nenhum tema encontrado (cursors/ ou manifest.hl)')
        package_name=source.name
        for suffix in ('.tar.gz','.tar.xz','.tar.bz2','.tar.zst','.tgz','.txz','.tbz2','.zip','.tar'):
            if package_name.lower().endswith(suffix):package_name=package_name[:-len(suffix)];break
        if not package_name or package_name.startswith('.'):raise ValueError('Nome de pacote inválido')
        root_names={p:package_name if p==payload else p.name for p in roots}
        names=list(root_names.values())
        if len(names)!=len(set(names)): raise ValueError('Temas com nomes duplicados')
        for p in roots:
            if (destination/root_names[p]).exists() or (destination/root_names[p]).is_symlink(): raise FileExistsError('Tema já instalado: '+root_names[p])
            # Cada tema deve ser autocontido, inclusive seus aliases.
            for root,dirs,files in os.walk(p,followlinks=False):
                for n in dirs+files:
                    q=Path(root)/n
                    if q.is_symlink() and not q.resolve().is_relative_to(p.resolve()): raise ValueError('Alias depende de outro tema')
            if (p/'cursors').is_dir():
                valid=False
                for q in (p/'cursors').iterdir():
                    if q.is_file():
                        try: preview(q,32);valid=True;break
                        except (ValueError,OSError): continue
                if not valid: raise ValueError('Tema sem imagem Xcursor válida: '+p.name)
            elif not (p/'manifest.hl').read_text().strip(): raise ValueError('Manifesto vazio')
        # renameat2 RENAME_NOREPLACE: proteção contra colisão concorrente.
        import ctypes
        libc=ctypes.CDLL(None,use_errno=True)
        rename=libc.renameat2;rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        installed=[]
        try:
            for p in roots:
                target=destination/root_names[p]
                if rename(-100,os.fsencode(p),-100,os.fsencode(target),1):
                    err=ctypes.get_errno();raise OSError(err,os.strerror(err),str(target))
                installed.append(target)
        except Exception:
            for p in installed: shutil.rmtree(p)
            raise
        return installed
