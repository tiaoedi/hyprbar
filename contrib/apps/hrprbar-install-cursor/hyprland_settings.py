"""Read-only discovery and explicitly requested Lua persistence for Hyprland.

Native flattened hl.config keys: wiki.hypr.land/configuring/core/config-options/.
No configuration is executed for syntax validation.
"""
from __future__ import annotations
import json
import math
import re
import difflib
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import uuid
import time

BEGIN = '-- hrprbar-settings:begin'
END = '-- hrprbar-settings:end'


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=15, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'Comando falhou: {args[0]}')
    return result.stdout


def managed_config(original, changes):
    text = original.decode('utf-8')
    entries = {}
    if BEGIN in text or END in text:
        if text.count(BEGIN)!=1 or text.count(END)!=1:
            raise ValueError('Marcadores do bloco gerenciado inválidos')
        prefix, rest = text.split(BEGIN)
        body, tail = rest.split(END)
        if tail.strip():
            raise ValueError('O bloco gerenciado deve estar no fim do arquivo')
        lines=body.strip().splitlines()
        if len(lines)<3 or not lines[0].startswith('-- valores: ') or lines[1]!='hl.config({' or lines[-1]!='})':
            raise ValueError('Bloco gerenciado alterado; revise no editor avançado')
        entries=json.loads(lines[0][12:])
        if not isinstance(entries,dict) or render_block(entries).splitlines()[1:-1] != body.strip().splitlines():
            raise ValueError('Conteúdo do bloco gerenciado não corresponde aos valores')
    else:
        prefix=text
    entries.update(changes)
    return (prefix.rstrip('\n')+'\n\n'+render_block(entries)+'\n').encode('utf-8')


def render_block(entries):
    for name in entries:
        if not re.fullmatch(r'[A-Za-z0-9_.:-]+',name) or name.replace(':','.')=='debug.manual_crash':
            raise ValueError('Nome de opção inválido ou bloqueado')
    return '\n'.join([BEGIN,'-- valores: '+json.dumps(entries,ensure_ascii=True,sort_keys=True), 'hl.config({', *[f'    [{lua_value(name.replace(":", "."))}] = {lua_value(value)},' for name,value in sorted(entries.items())], '})',END])


class Document:
    def __init__(self,path,runner=run):
        self.path=Path(path).absolute()
        self.target=self.path.resolve(strict=True)
        if self.target.suffix!='.lua':
            raise ValueError('Somente configuração Lua é suportada')
        self.original=self.target.read_bytes()
        self.identity=self.target.stat()
        self.runner=runner

    def check_current(self):
        now=self.target.stat()
        if self.path.resolve(strict=True)!=self.target or self.target.read_bytes()!=self.original or (now.st_ino,now.st_dev,now.st_mode)!=(self.identity.st_ino,self.identity.st_dev,self.identity.st_mode):
            raise ValueError('Configuração mudou em outro processo; releia antes de salvar')

    def validate(self,content):
        content.decode('utf-8')
        with tempfile.NamedTemporaryFile(suffix='.lua') as stream:
            stream.write(content);stream.flush()
            self.runner(['luac','-p',stream.name])

    def diff(self,content):
        return ''.join(difflib.unified_diff(self.original.decode('utf-8').splitlines(True),content.decode('utf-8').splitlines(True),fromfile=str(self.target),tofile='proposto'))

    def save(self,content):
        self.check_current()
        self.validate(content)
        self.check_current()
        backup=self.target.with_name(self.target.name+'.backup-'+uuid.uuid4().hex)
        fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,stat.S_IMODE(self.identity.st_mode))
        with os.fdopen(fd,'wb') as stream:
            stream.write(self.original);stream.flush();os.fsync(stream.fileno())
        if backup.read_bytes()!=self.original:
            raise OSError('Verificação do backup falhou; nada foi substituído')
        replaced=False
        try:
            self._replace(content)
            replaced=True
            if self.target.read_bytes()!=content:
                raise OSError('Verificação após gravação falhou')
        except Exception as exc:
            if replaced:
                try:
                    self._replace(self.original,rollback=True)
                    if self.target.read_bytes()!=self.original:
                        raise OSError('Leitura de restauração divergente')
                except Exception as rollback:
                    error=OSError(f'Falha na gravação: {exc}; restauração falhou: {rollback}; backup: {backup}')
                    error.backup=backup
                    raise error from exc
            error=OSError(f'Falha na gravação: {exc}; arquivo original preservado/restaurado; backup: {backup}')
            error.backup=backup
            raise error from exc
        self.original=content;self.identity=self.target.stat()
        return backup

    def _replace(self,content,rollback=False):
        fd,name=tempfile.mkstemp(prefix='.'+self.target.name+'.',dir=self.target.parent)
        try:
            with os.fdopen(fd,'wb') as stream:
                os.fchmod(stream.fileno(),stat.S_IMODE(self.identity.st_mode))
                stream.write(content);stream.flush();os.fsync(stream.fileno())
            if not rollback:self.check_current()
            os.replace(name,self.target)
        finally:
            if os.path.exists(name):os.unlink(name)


def lua_value(value):
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) in (int, float):
        if not math.isfinite(value):
            raise ValueError('Número não finito')
        return repr(value)
    if isinstance(value, str):
        return '"' + ''.join(('\\"' if c == '"' else '\\\\' if c == '\\' else '\\n' if c == '\n' else '\\r' if c == '\r' else '\\t' if c == '\t' else f'\\{ord(c):03d}' if ord(c)<32 or ord(c)==127 else c) for c in value) + '"'
    raise ValueError('Tipo sem serialização Lua segura')


class Runtime:
    def __init__(self,runner=run,proc=Path('/proc'),environ=None):
        self.runner=runner
        env=os.environ if environ is None else environ
        instances=json.loads(runner(['hyprctl','instances','-j']))
        display=env.get('WAYLAND_DISPLAY')
        matches=[item for item in instances if item.get('wl_socket')==display] if display else [item for item in instances if item.get('instance')==env.get('HYPRLAND_INSTANCE_SIGNATURE')]
        if len(matches)!=1:
            raise ValueError('Não foi possível identificar uma única sessão Hyprland para este WAYLAND_DISPLAY')
        self.instance=matches[0]
        base=Path(proc)/str(self.instance['pid'])
        self.binary=(base/'exe').resolve(strict=True)
        argv=[os.fsdecode(part) for part in (base/'cmdline').read_bytes().split(b'\0') if part]
        process_env=dict(os.fsdecode(part).split('=',1) for part in (base/'environ').read_bytes().split(b'\0') if b'=' in part)
        config=None
        for index,arg in enumerate(argv):
            if arg in ('-c','--config'):
                if index+1>=len(argv):raise ValueError('Argumento --config incompleto')
                config=argv[index+1]
            elif arg.startswith('--config='):config=arg.split('=',1)[1]
        if config:
            self.config=Path(config)
            if not self.config.is_absolute():self.config=(base/'cwd').resolve(strict=True)/self.config
        else:
            home=process_env.get('HOME')
            if not home:raise ValueError('HOME do compositor indisponível')
            self.config=Path(process_env.get('XDG_CONFIG_HOME',str(Path(home)/'.config')))/'hypr/hyprland.lua'
        if not self.config.is_file():raise ValueError('Configuração Lua ativa não encontrada: '+str(self.config))

    def command(self,*args):
        return self.runner(['hyprctl','-i',self.instance['instance'],*args])

    def options(self):
        data=json.loads(self.command('descriptions','-j'))
        if not isinstance(data,list) or not data:raise ValueError('Catálogo de opções ausente ou inválido')
        options=[Option(raw) for raw in data]
        if len({option.name for option in options})!=len(options):raise ValueError('Catálogo com nomes duplicados')
        return options

    def ensure_save_safe(self):
        value=json.loads(self.command('getoption','misc:disable_autoreload','-j'))
        if value.get('bool') is not True and not ('bool' not in value and value.get('int')==1):
            raise ValueError('Salvar foi bloqueado: a recarga automática do Hyprland está ativa. Desative explicitamente misc.disable_autoreload antes de gravar; salvar o arquivo poderia executar hooks sem confirmação. Nenhuma opção foi alterada.')

    def disable_autoreload(self):
        self.command('eval','hl.config({["misc.disable_autoreload"] = true})')
        self.ensure_save_safe()

    def reload(self):
        reply=self.command('reload')
        errors=self.command('configerrors')
        if errors.strip():raise RuntimeError('Recarga solicitada, mas há erros de configuração: '+errors)
        return reply

    def readback(self,names):
        return {name:json.loads(self.command('getoption',name,'-j')) for name in names}


def observed_scalar(raw, expected):
    """Decode only the native scalar schema, never a missing-field equality."""
    kind = type(expected)
    keys = {bool: ('bool', 'int'), int: ('int',), float: ('float', 'int'), str: ('str',)}
    for key in keys[kind]:
        if key not in raw:
            continue
        value = raw[key]
        if kind is bool:
            if key == 'bool' and type(value) is bool:
                return value
            if key == 'int' and type(value) is int and value in (0, 1):
                return bool(value)
        elif kind is int and type(value) is int:
            return value
        elif kind is float and type(value) in (int, float) and math.isfinite(value):
            return float(value)
        elif kind is str and type(value) is str:
            return value
        raise ValueError('Tipo de leitura incompatível: '+repr(raw))
    raise ValueError('Leitura escalar ausente: '+repr(raw))


def apply_changes(runtime, document, content, changes, *, verify_timeout=3.0, poll_interval=.1):
    """Confirmed save/reload/readback transaction; never roll back live Lua."""
    backup = None
    try:
        document.validate(content)
        document.check_current()
        safe = observed_scalar(runtime.readback(['misc:disable_autoreload'])['misc:disable_autoreload'], True)
        if not safe:
            runtime.disable_autoreload()
        runtime.ensure_save_safe()
        backup = document.save(content)
        runtime.reload()
        deadline = time.monotonic() + verify_timeout
        while True:
            try:
                raw = runtime.readback(list(changes)) if changes else {}
                observed = {name: observed_scalar(raw[name], value) for name, value in changes.items()}
                mismatches = {name: (value, observed[name]) for name, value in changes.items() if observed[name] != value}
                if mismatches:
                    raise ValueError('Valores divergentes (esperado, observado): '+repr(mismatches))
                # Preserve an already-disabled session guard, unless explicitly edited.
                if safe and 'misc:disable_autoreload' not in changes:
                    if not observed_scalar(runtime.readback(['misc:disable_autoreload'])['misc:disable_autoreload'], True):
                        runtime.disable_autoreload()
                    runtime.ensure_save_safe()
                break
            except Exception:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
                time.sleep(min(poll_interval, remaining))
        return {'saved': True, 'verified': True, 'backup': backup, 'observed': observed, 'error': None}
    except Exception as exc:
        return {'saved': backup is not None, 'verified': False, 'backup': getattr(exc,'backup',backup), 'observed': {}, 'error': str(exc)}


class Option:
    def __init__(self, raw):
        self.raw = dict(raw)
        self.name = raw['name']
        self.current = raw.get('current')
        # Hyprland descriptions serialize integral FLOAT opacity values as JSON
        # integers (1), although getoption reports float: 1.000000. Normalize
        # only these documented scalar keys; never infer arbitrary int schemas.
        if self.name in ('decoration:active_opacity', 'decoration:inactive_opacity',
                         'decoration:fullscreen_opacity') and type(self.current) in (int, float):
            self.current = float(self.current)
            self.raw['current'] = self.current
        self.category = self.name.rsplit(':', 1)[0] if ':' in self.name else 'geral'
        native_color = isinstance(self.current,str) and (bool(re.search(r'\b[0-9a-fA-F]{8}\b',self.current)) or self.current.endswith('deg')) and any(token in self.name for token in ('col.','color','tint'))
        native_gaps = self.name in ('general:gaps_in','general:gaps_out','general:float_gaps')
        self.editable = self.name != 'debug:manual_crash' and not native_color and not native_gaps and type(self.current) in (bool,int,float,str)
        self.reason = ('Bloqueado: esta opção pode encerrar o compositor.' if self.name == 'debug:manual_crash' else 'Cor/gradiente ou tipo composto/nulo sem conversão Lua verificada: consulte os dados brutos e use o editor Lua avançado.' if not self.editable else 'Validação de tipo local; a semântica será verificada pelo compositor após recarga explícita.')

    def parse(self, text):
        if not self.editable:
            raise ValueError(self.reason)
        kind = type(self.current)
        try:
            if kind is bool:
                if text.lower() not in ('true','false'):
                    raise ValueError('Use true ou false')
                value = text.lower() == 'true'
            elif kind is int:
                if not re.fullmatch(r'[+-]?\d+',text):
                    raise ValueError('Use um número inteiro')
                value = int(text)
            elif kind is float:
                value = float(text)
                if not math.isfinite(value):
                    raise ValueError('Número não finito')
            else:
                value = text
        except (ValueError, OverflowError) as exc:
            raise ValueError('Valor inválido: '+str(exc)) from exc
        if kind in (int,float):
            for bound, comparison in (('min', lambda a,b:a<b),('max',lambda a,b:a>b)):
                limit = self.raw.get(bound)
                if type(limit) in (int,float) and comparison(value,limit):
                    raise ValueError(f'Fora do limite {bound}: {limit}')
        return value
