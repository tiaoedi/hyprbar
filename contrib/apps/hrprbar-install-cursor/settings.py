"""Persistência explícita com backups e diagnóstico sem prometer hot-switch universal."""
from __future__ import annotations
import configparser
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid


def snap_size(requested: int, sizes: list[int]) -> int:
    if not sizes: raise ValueError('Tema sem tamanhos disponíveis')
    return min(sizes,key=lambda s:(abs(s-requested),s))


def matches(theme: str, size: str, wanted: str, pixels: int) -> bool:
    return theme.strip("'\"\n ")==wanted and size.strip()==str(pixels)


def prepare_xcb_theme(theme, home: Path) -> list[str]:
    """Prepare legacy XCB file lookup; this does not prove a visual hot-switch."""
    if (not re.fullmatch(r'[\w .+()@-]+', theme.name)
            or theme.name in ('.', '..') or theme.name != theme.name.strip()):
        raise ValueError('Nome de tema inválido para XCB')
    icons = home / '.icons'
    source = theme.path.resolve(strict=True)
    if not source.is_dir():
        raise ValueError('Origem do tema não é diretório')
    alias = icons / theme.name
    if (alias.exists() or alias.is_symlink()) and alias.resolve() != source:
        raise ValueError('Alias XCB conflitante: ' + str(alias))
    diagnostics = []
    created = False
    default = icons / 'default/index.theme'
    target = default.resolve()
    if (theme.name != 'default' and
            ((source != home.resolve() and target.is_relative_to(source))
             or (target.parent / 'cursors').is_dir())):
        raise ValueError('Fallback XCB aponta para a origem de um tema: ' + str(target))
    old = target.read_bytes() if target.exists() else None
    text = old.decode('utf-8') if old is not None else '[Icon Theme]\n'
    icons.mkdir(parents=True, exist_ok=True)
    if theme.name != 'default':
        default.parent.mkdir(parents=True, exist_ok=True)
    if not alias.exists() and not alias.is_symlink():
        alias.symlink_to(source, target_is_directory=True)
        created = True
        diagnostics.append('Criado alias XCB: ' + str(alias))
    if theme.name == 'default':
        diagnostics.append('VERIFICADO fallback XCB (diretório default, sem auto-herança): ' + str(alias))
        return diagnostics
    lines = text.splitlines(keepends=True)
    in_theme = False
    found = False
    for index, line in enumerate(lines):
        if re.match(r'^\s*\[', line):
            if in_theme and not found:
                lines.insert(index, 'Inherits=' + theme.name + '\n')
                found = True
                break
            in_theme = line.strip() == '[Icon Theme]'
        elif in_theme and re.match(r'^\s*Inherits\s*=', line):
            lines[index] = 'Inherits=' + theme.name + '\n'
            found = True
    if not found:
        if not in_theme:
            lines.append('\n[Icon Theme]\n')
        elif lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        lines.append('Inherits=' + theme.name + '\n')
    data = ''.join(lines).encode('utf-8')
    replaced = False
    try:
        if data != old:
            if old is not None:
                backup = target.with_name(target.name + '.bak-' + uuid.uuid4().hex)
                shutil.copy2(target, backup)
                diagnostics.append('Backup XCB: ' + str(backup))
            fd, tmp = tempfile.mkstemp(prefix='.' + target.name, dir=target.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                if target.exists():
                    os.chmod(tmp, target.stat().st_mode & 0o777)
                os.replace(tmp, target)
                replaced = True
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        if target.read_bytes() != data:
            raise OSError('Falha de verificação XCB: ' + str(target))
    except Exception:
        if replaced:
            if old is None:
                target.unlink()
            else:
                target.write_bytes(old)
        if created and alias.is_symlink() and alias.resolve() == source:
            alias.unlink()
        raise
    diagnostics.append('VERIFICADO fallback XCB (arquivos): ' + str(default))
    return diagnostics


def persist(theme, size: int, home: Path, config_home: Path | None = None, *, xcb_diagnostics: list[str] | None = None) -> list[str]:
    if not theme.xcursor: raise ValueError('Hyprcursor puro não oferece aplicação unificada')
    if not re.fullmatch(r'[\w .+()@-]+',theme.name): raise ValueError('Nome de tema contém caracteres não suportados para aplicação')
    config_home=config_home or home/'.config'
    hypr=(config_home/'hypr/hyprland.lua').resolve(strict=True)
    text=hypr.read_text()
    for key,value in {'XCURSOR_THEME':theme.name,'HYPRCURSOR_THEME':theme.name,'XCURSOR_SIZE':str(size),'HYPRCURSOR_SIZE':str(size)}.items():
        pattern=r'(?m)^(\s*hl\.env\(\s*[\"\x27]'+key+r'[\"\x27]\s*,\s*)[\"\x27][^\"\x27]*[\"\x27](\s*\).*)$'
        text,n=re.subn(pattern,lambda m:m[1]+json.dumps(value,ensure_ascii=False)+m[2],text)
        if not n: text+='\nhl.env('+json.dumps(key)+', '+json.dumps(value,ensure_ascii=False)+')\n'
    text,n=re.subn(r'(\benable_hyprcursor\s*=\s*)(true|false)',r'\g<1>false',text)
    if not n: text+='\nhl.config({ cursor = { enable_hyprcursor = false } })\n'
    changes={hypr:text}
    for version in ('3.0','4.0'):
        path=(config_home/f'gtk-{version}/settings.ini').resolve()
        parser=configparser.ConfigParser(interpolation=None);parser.optionxform=str
        if path.exists(): parser.read_string(path.read_text())
        if not parser.has_section('Settings'): parser.add_section('Settings')
        parser['Settings']['gtk-cursor-theme-name']=theme.name
        parser['Settings']['gtk-cursor-theme-size']=str(size)
        out=io.StringIO();parser.write(out);changes[path]=out.getvalue()
    path=(home/'.Xresources').resolve()
    resources=path.read_text() if path.exists() else ''
    resources=re.sub(r'(?ms)^! BEGIN hrprbar-install cursor\n.*?^! END hrprbar-install cursor\n?','',resources)
    resources+='\n! BEGIN hrprbar-install cursor\nXcursor.theme: '+theme.name+'\nXcursor.size: '+str(size)+'\n! END hrprbar-install cursor\n'
    changes[path]=resources
    backups=[];written=[]
    try:
        for path,data in changes.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            old=path.read_bytes() if path.exists() else None
            if old is not None:
                backup=path.with_name(path.name+'.bak-'+uuid.uuid4().hex)
                shutil.copy2(path,backup);backups.append(str(backup))
            fd,tmp=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
            try:
                with os.fdopen(fd,'w') as stream: stream.write(data)
                if path.exists(): os.chmod(tmp,path.stat().st_mode & 0o777)
                os.replace(tmp,path)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
            written.append((path,old))
        for path,data in changes.items():
            if path.read_text()!=data: raise OSError('Falha de verificação: '+str(path))
        legacy = prepare_xcb_theme(theme, home)
        if xcb_diagnostics is not None:
            xcb_diagnostics.extend(legacy)
    except Exception:
        for path,old in reversed(written):
            if old is None: path.unlink(missing_ok=True)
            else: path.write_bytes(old)
        raise
    return [str(path) for path in changes]


def run(args: list[str], data: str | None = None) -> tuple[bool,str]:
    try:
        if args and args[0] == 'hyprctl' and '-i' not in args and args[1:2] != ['instances']:
            discovery = subprocess.run(['hyprctl', 'instances', '-j'], text=True, capture_output=True, timeout=12)
            if discovery.returncode:
                return False, 'Falha ao descobrir sessão Hyprland: ' + (discovery.stdout + discovery.stderr).strip()
            try:
                instances = json.loads(discovery.stdout)
                if not isinstance(instances, list) or not all(isinstance(item, dict) for item in instances):
                    raise ValueError('resposta inválida')
                display = os.environ.get('WAYLAND_DISPLAY')
                matches = [item for item in instances if item.get('wl_socket') == display] if display else [item for item in instances if item.get('instance') == os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')]
                if len(matches) != 1 or not isinstance(matches[0].get('instance'), str) or not matches[0]['instance']:
                    raise ValueError('não foi possível identificar uma única sessão para WAYLAND_DISPLAY')
                args = ['hyprctl', '-i', matches[0]['instance'], *args[1:]]
            except ValueError as exc:
                return False, 'Descoberta Hyprland inválida: ' + str(exc)
        p=subprocess.run(args,input=data,text=True,capture_output=True,timeout=12)
        return p.returncode==0,(p.stdout+p.stderr).strip()
    except (OSError,subprocess.TimeoutExpired) as exc: return False,str(exc)


def stale_apps(theme: str,size: int) -> list[dict]:
    ok,output=run(['hyprctl','clients','-j'])
    if not ok: return []
    try: pids={c['pid'] for c in json.loads(output) if c.get('pid')}
    except (ValueError,KeyError): return []
    result=[]
    for pid in sorted(pids):
        try:
            proc=Path('/proc')/str(pid)
            env=dict(x.split(b'=',1) for x in (proc/'environ').read_bytes().split(b'\0') if b'=' in x)
            current=env.get(b'XCURSOR_THEME',b'').decode(errors='replace'); pixels=env.get(b'XCURSOR_SIZE',b'').decode(errors='replace')
            exe=os.readlink(proc/'exe')
            if not matches(current,pixels,theme,size): result.append({'pid':pid,'exe':exe,'theme':current or '(ausente)','size':pixels or '(ausente)'})
        except (OSError,ValueError): continue
    return result


def apply(theme,size: int, *, home: Path | None = None, runner=None, inspect_apps: bool = True) -> str:
    injected=home is not None
    home=home or Path.home();cfg=home/'.config' if injected else Path(os.environ.get('XDG_CONFIG_HOME',home/'.config'))
    execute=runner or run
    legacy = []
    files=persist(theme,size,home,cfg,xcb_diagnostics=legacy)
    lines=['Arquivos gravados e relidos: '+', '.join(files), *legacy]
    lines.append('Fallback XCB verificado em arquivos NÃO comprova o cursor visual; caches de toolkits não são invalidados universalmente.')
    commands=[('GSettings tema',['gsettings','set','org.gnome.desktop.interface','cursor-theme',theme.name]),('GSettings tamanho',['gsettings','set','org.gnome.desktop.interface','cursor-size',str(size)]),('Xresources',['xrdb','-merge']),('Ativação D-Bus/systemd',['dbus-update-activation-environment','--systemd','XCURSOR_THEME='+theme.name,'XCURSOR_SIZE='+str(size),'HYPRCURSOR_THEME='+theme.name,'HYPRCURSOR_SIZE='+str(size)]),('Hyprland recarregar',['hyprctl','reload']),('Hyprland cursor',['hyprctl','setcursor',theme.name,str(size)])]
    for label,args in commands:
        ok,output=execute(args, f'Xcursor.theme: {theme.name}\nXcursor.size: {size}\n' if args[0]=='xrdb' else None)
        lines.append(('OK ' if ok else 'FALHA ')+label+(': '+output[:600] if output else ''))
    checks=[('GSettings tema',['gsettings','get','org.gnome.desktop.interface','cursor-theme']),('GSettings tamanho',['gsettings','get','org.gnome.desktop.interface','cursor-size']),('Xresources runtime',['xrdb','-query']),('systemd ambiente',['systemctl','--user','show-environment']),('Hyprland modo Xcursor',['hyprctl','getoption','cursor:enable_hyprcursor','-j']),('Hyprland erros',['hyprctl','configerrors']),('Monitores / escalas',['hyprctl','monitors','-j'])]
    for label,args in checks:
        ok,out=execute(args)
        if label=='systemd ambiente': out='\n'.join(x for x in out.splitlines() if x.startswith(('XCURSOR_','HYPRCURSOR_'))); valid=all(v in out for v in ('XCURSOR_THEME='+theme.name,'XCURSOR_SIZE='+str(size)))
        elif label=='GSettings tema': valid=out.strip("'\"")==theme.name
        elif label=='GSettings tamanho': valid=out==str(size)
        elif label=='Xresources runtime':
            out='\n'.join(x for x in out.splitlines() if x.startswith('Xcursor.'));valid=bool(re.search(r'Xcursor.theme:\s*'+re.escape(theme.name)+r'\s*$',out,re.M) and re.search(r'Xcursor.size:\s*'+str(size)+r'\s*$',out,re.M))
        elif label=='Hyprland modo Xcursor':
            try:
                option=json.loads(out)
                valid=isinstance(option,dict) and (option.get('bool') is False or ('bool' not in option and option.get('int')==0))
            except ValueError: valid=False
        elif label=='Hyprland erros': valid=not out
        else:
            try: out='; '.join(m['name']+' escala '+str(m['scale']) for m in json.loads(out));valid=True
            except (ValueError,KeyError): valid=False
        lines.append(('VERIFICADO ' if ok and valid else 'NÃO CONFIRMADO ')+label+': '+out[:1000])
    lines.append('Mesmo tema Xcursor; tamanho nominal '+str(size)+'. Escalas diferentes podem alterar pixels físicos. O compositor não expõe confirmação visual do desenho; cache de aplicativos não é invalidado universalmente.')
    pending=stale_apps(theme.name,size) if inspect_apps else []
    lines.append('Ambiente antigo/ausente NÃO prova cache incorreto; ambiente compatível NÃO prova desenho atualizado.')
    lines.extend(f"PID {p['pid']} {Path(p['exe']).name}: tema={p['theme']}, tamanho={p['size']} — reabra se necessário" for p in pending)
    lines.append('Nenhum aplicativo foi reiniciado. Aplicativos em sandbox podem ignorar o tema do host.')
    return '\n'.join(lines)
