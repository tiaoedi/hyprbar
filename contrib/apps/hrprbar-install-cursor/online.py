"""Public GitHub release packages; never execute downloaded content."""
from __future__ import annotations
from dataclasses import dataclass
import json
import re
import hashlib
import os
from pathlib import Path
import tempfile
import cursor_manager as cm
from urllib.parse import urlsplit, unquote
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError, URLError
from contextlib import contextmanager
from http.client import IncompleteRead


@contextmanager
def response_for(request: Request, repo: str | None, opener=None):
    try:
        with (opener(request, timeout=TIMEOUT) if opener else open_safe(request, repo)) as response:
            yield response
    except HTTPError as exc:
        exc.close()
        if exc.code == 404:
            message = 'Repositório não encontrado, privado ou sem releases publicadas (404).'
        elif exc.code in (403, 429):
            message = 'Acesso recusado ou limite da API GitHub atingido; aguarde e tente novamente.'
        else:
            message = f'GitHub respondeu HTTP {exc.code}; tente novamente mais tarde.'
        raise ValueError(message) from exc
    except TimeoutError as exc:
        raise ValueError('Tempo de conexão esgotado; tente novamente.') from exc
    except (URLError, IncompleteRead, ConnectionError) as exc:
        raise ValueError('Falha de conexão ou download interrompido; tente novamente.') from exc



class SafeRedirect(HTTPRedirectHandler):
    """Reject redirect targets before urllib sends any request to them."""
    def __init__(self, repo: str | None):
        self.repo = repo
        super().__init__()

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        path = unquote(parsed.path)
        allowed = (self.repo is not None and parsed.scheme == 'https' and not parsed.fragment
                   and not any(ord(c) < 32 for c in newurl)
                   and (parsed.netloc == 'release-assets.githubusercontent.com'
                        or (parsed.netloc == 'github.com' and path.startswith('/'+self.repo+'/releases/download/')
                            and not parsed.query and not any(p in ('.', '..') for p in path.split('/')))))
        if not allowed:
            raise ValueError('Redirecionamento inseguro recusado; somente assets HTTPS do GitHub são permitidos.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_safe(request: Request, repo: str | None):
    return build_opener(SafeRedirect(repo)).open(request, timeout=TIMEOUT)


FAMILIES = {
    'Bibata': 'ful1e5/Bibata_Cursor',
    'BreezeX': 'ful1e5/BreezeX_Cursor',
    'GoogleDot': 'ful1e5/Google_Cursor',
    'macOS': 'ful1e5/apple_cursor',
    'Fuchsia': 'ful1e5/fuchsia-cursor',
}
TIMEOUT = 20
MAX_METADATA = 2 * 1024 * 1024
MAX_DOWNLOAD = 64 * 1024 * 1024

@dataclass(frozen=True)
class Asset:
    repo: str
    version: str
    name: str
    size: int
    url: str
    digest: str | None = None


def repository(value: str) -> str:
    value = value.strip()
    if value.startswith('https://github.com/'):
        value = value[len('https://github.com/'):]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}', value) or value.split('/')[1] in ('.', '..'):
        raise ValueError('Informe owner/repo ou https://github.com/owner/repo (sem parâmetros).')
    return value


def latest(value: str, *, opener=None) -> list[Asset]:
    repo = repository(value)
    request = Request(f'https://api.github.com/repos/{repo}/releases/latest', headers={
        'User-Agent': 'hrprbar-install-cursor', 'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'})
    with response_for(request, None, opener) as response:
        data = response.read(MAX_METADATA + 1)
    if len(data) > MAX_METADATA:
        raise ValueError('Resposta do catálogo grande demais.')
    try:
        release = json.loads(data)
        if not isinstance(release, dict) or not isinstance(release.get('assets'), list) or not isinstance(release.get('tag_name'), str):
            raise ValueError('Resposta inválida do catálogo: versão/assets ausentes.')
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Resposta inválida do catálogo GitHub.') from exc
    result = []
    for item in release.get('assets', []):
        if not isinstance(item, dict) or not isinstance(item.get('name', ''), str):
            raise ValueError('Item inválido no catálogo GitHub.')
        name = item.get('name', '')
        if not name.lower().endswith(('.tar.xz', '.tar.gz', '.tar.bz2', '.tgz', '.txz')):
            continue
        try:
            asset = Asset(repo, release['tag_name'], name, item['size'], item['browser_download_url'], item.get('digest'))
            validate_asset(asset)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('Pacote inválido no catálogo: '+str(exc)) from exc
        result.append(asset)
    if not result:
        raise ValueError('A última versão não contém pacotes Linux de temas (.tar.xz/.tar.gz).')
    return result


@dataclass(frozen=True)
class Catalog:
    assets: tuple[Asset, ...]
    statuses: dict[str, str]


def catalog(repos: list[str] | None = None) -> Catalog:
    """One repository failure never discards other publishers' packages."""
    from concurrent.futures import ThreadPoolExecutor
    sources = list(dict.fromkeys(repository(r) for r in (repos if repos is not None else FAMILIES.values())))
    assets: list[Asset] = []
    statuses: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        pending = {repo: pool.submit(latest, repo) for repo in sources}
        for repo, future in pending.items():
            try:
                found = future.result()
                assets.extend(found)
                statuses[repo] = f'{len(found)} pacote(s) • {found[0].version}'
            except Exception as exc:
                statuses[repo] = 'Falha: '+str(exc)
    return Catalog(tuple(assets), statuses)


def validate_asset(asset: Asset) -> None:
    repo = repository(asset.repo)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]{0,180}', asset.name) or not asset.name.lower().endswith(('.tar.xz', '.tar.gz', '.tar.bz2', '.tgz', '.txz')):
        raise ValueError('Nome de pacote Linux inválido.')
    if type(asset.size) is not int or not 0 < asset.size <= MAX_DOWNLOAD:
        raise ValueError('Pacote vazio ou excede o limite de 64 MiB.')
    parsed = urlsplit(asset.url)
    path = unquote(parsed.path)
    if (parsed.scheme != 'https' or parsed.netloc != 'github.com' or parsed.query or parsed.fragment
            or not path.startswith('/'+repo+'/releases/download/')
            or any(part in ('.', '..') for part in path.split('/'))
            or '\\' in path or any(ord(c) < 32 for c in asset.url)
            or path.split('/')[-1] != asset.name):
        raise ValueError('URL de download não pertence à release do repositório informado.')
    if asset.digest is not None and not re.fullmatch(r'sha256:[0-9a-f]{64}', asset.digest):
        raise ValueError('Digest SHA256 inválido no catálogo.')


def install_asset(asset: Asset, destination: Path, *, opener=None, scratch: Path | None = None) -> list[Path]:
    validate_asset(asset)
    with tempfile.TemporaryDirectory(prefix='cursor-download-', dir=scratch or os.environ.get('TMPDIR')) as temporary:
        package = Path(temporary) / asset.name
        digest = hashlib.sha256()
        request = Request(asset.url, headers={'User-Agent': 'hrprbar-install-cursor'})
        with response_for(request, asset.repo, opener) as response, package.open('wb') as stream:
            length = response.headers.get('Content-Length')
            if length is not None and (not length.isdigit() or int(length) > MAX_DOWNLOAD):
                raise ValueError('Tamanho HTTP inválido ou excede o limite de 64 MiB.')
            total = 0
            while chunk := response.read(64 * 1024):
                total += len(chunk)
                if total > MAX_DOWNLOAD:
                    raise ValueError('Pacote excede o limite de 64 MiB.')
                digest.update(chunk)
                stream.write(chunk)
        if total != asset.size:
            raise ValueError('Download incompleto: tamanho diferente do catálogo.')
        if asset.digest and asset.digest != 'sha256:' + digest.hexdigest():
            raise ValueError('SHA256 do pacote não confere; instalação recusada.')
        try:
            return cm.install(package, destination)
        except FileExistsError as exc:
            raise FileExistsError('Tema já instalado; nenhum tema existente será sobrescrito.') from exc
