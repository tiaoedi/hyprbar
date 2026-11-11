"""Curated icon artwork provenance; only verified pinned packages are installable."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.request import HTTPRedirectHandler


class RejectRedirect(HTTPRedirectHandler):
    """Pinned codeload snapshots must never redirect, even within GitHub."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirecionamento recusado para pacote fixado.')


def install_source(source: Source, destination: Path, *, opener=None, scratch: Path | None = None) -> list[Path]:
    """Install one exact catalog object, never apply it or execute upstream code.

    ``opener`` is a trusted test/transport injection; the default urllib opener
    refuses every redirect before sending the redirected request. Both paths
    must deliver the pinned byte count and SHA256 before archive extraction.
    """
    if type(source) is not Source or not any(source is item for item in SOURCES):
        raise ValueError('Fonte não pertence ao catálogo verificado.')
    if source.package is None:
        raise ValueError(source.reason)
    import hashlib
    import os
    import re
    import tempfile
    from urllib.request import Request, build_opener
    import icons
    import online

    artifact = source.package
    if (type(artifact) is not Package or artifact.repo != 'Morzilla/neoline-icons'
            or not re.fullmatch(r'[0-9a-f]{40}', artifact.commit)
            or artifact.name != 'NeoLine.tar.gz'
            or not re.fullmatch(r'https://codeload\.github\.com/Morzilla/neoline-icons/tar\.gz/[0-9a-f]{40}', artifact.url)):
        raise ValueError('URL ou pacote fora da origem fixada verificada.')
    if type(artifact.size) is not int or not 0 < artifact.size <= online.MAX_DOWNLOAD:
        raise ValueError('Pacote vazio ou excede 64 MiB.')
    if not re.fullmatch(r'[0-9a-f]{64}', artifact.sha256):
        raise ValueError('SHA256 inválido no catálogo.')
    with tempfile.TemporaryDirectory(prefix='icon-catalog-', dir=scratch or os.environ.get('TMPDIR')) as temporary:
        package = Path(temporary)/artifact.name
        total = 0
        digest = hashlib.sha256()
        open_package = opener or build_opener(RejectRedirect()).open
        with open_package(Request(artifact.url, headers={'User-Agent': 'hrprbar-install-cursor'}), timeout=20) as response, package.open('wb') as stream:
            if getattr(response, 'status', 200) != 200:
                raise ValueError('Resposta HTTP não é um pacote completo (200).')
            final_url = response.geturl() if hasattr(response, 'geturl') else None
            if final_url is not None and final_url != artifact.url:
                raise ValueError('Redirecionamento recusado para pacote fixado.')
            length = response.headers.get('Content-Length')
            if length is not None and (not re.fullmatch(r'[0-9]{1,20}', length) or int(length) != artifact.size):
                raise ValueError('Tamanho HTTP inválido ou diferente do catálogo.')
            while chunk := response.read(65536):
                total += len(chunk)
                if total > min(artifact.size, online.MAX_DOWNLOAD):
                    raise ValueError('Pacote excede tamanho do catálogo ou 64 MiB.')
                digest.update(chunk)
                stream.write(chunk)
        if total != artifact.size:
            raise ValueError('Download incompleto: tamanho diferente do catálogo.')
        if digest.hexdigest() != artifact.sha256:
            raise ValueError('SHA256 não confere; instalação recusada.')
        return icons.install(package, destination)


@dataclass(frozen=True)
class Package:
    repo: str
    commit: str
    name: str
    size: int
    sha256: str

    @property
    def url(self) -> str:
        return f'https://codeload.github.com/{self.repo}/tar.gz/{self.commit}'


@dataclass(frozen=True)
class Source:
    key: str
    name: str
    author: str
    page: str
    license: str
    reason: str
    package: Package | None = None


SOURCES = (
    Source('mint-light', 'Mint Breeze Light Icons', 'dr-mccoy', 'https://www.gnome-look.org/p/2326678/', 'GPL-3.0',
           'Bloqueado: pacote 1.4.20 contém link quebrado (apps/48/plasma-browser-integration.svg).'),
    Source('nordic-slot', 'Nordic Slot Dark Icons', 'l4k1', 'https://www.gnome-look.org/p/2378240/', 'GPL-3.0',
           'Bloqueado: 36.217 entradas excedem o limite de 20.000.'),
    Source('buuf', 'Buuf For Many Desktops', 'nestort', 'https://www.gnome-look.org/p/1012233/',
           'Divergente: site CC-BY-SA; upstream cita CC-BY-NC-SA 2.5',
           'Bloqueado: pacote excede 64 MiB; licença precisa de revisão.'),
    Source('neoline', 'NeoLine', 'Morzilla', 'https://www.gnome-look.org/p/2381562/', 'MIT',
           'Verificado: NeoLine, NeoLine-White e NeoLine-Yellow; requer fallback Breeze Dark.',
           Package('Morzilla/neoline-icons', '30abd1093bf2ddc3689474a4ca94c53fb21ae74e', 'NeoLine.tar.gz', 2005766,
                   '61dc114ec3cf6c15e36a2387f0c34d95246c13c4d07c9ed7551f9ce3c5d60ec8')),
    Source('skeuo-art-deco', 'Skeuo-Silver-Art-Deco', 'artsailer', 'https://www.gnome-look.org/p/2376237/', 'GPL-3.0',
           'Bloqueado: pacote declarado 167.658 KiB excede 64 MiB.'),
    Source('mint-calm', 'Mint Breeze - Calm Green Icons', 'dr-mccoy', 'https://www.gnome-look.org/p/2324617/', 'GPL-3.0',
           'Bloqueado: pacote 1.4.20 contém dois links quebrados.'),
)
