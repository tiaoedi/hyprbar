"""Leitura somente de IPC/paleta do Hyprbar; nenhum hook ou reload."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote

DARK={'mPrimary':'#c4a7e7','mOnPrimary':'#191724','mSecondary':'#f6c177','mSurface':'#191724','mOnSurface':'#e0def4','mSurfaceVariant':'#26233a','mOnSurfaceVariant':'#908caa','mOutline':'#403d52','mHover':'#6c6887','mOnHover':'#191724','mError':'#eb6f92'}
LIGHT={'mPrimary':'#907aa9','mOnPrimary':'#faf4ed','mSecondary':'#a05d09','mSurface':'#fffaf3','mOnSurface':'#575279','mSurfaceVariant':'#f2e9e1','mOnSurfaceVariant':'#797593','mOutline':'#dfdad9','mHover':'#cecacd','mOnHover':'#575279','mError':'#b4637a'}


def resolve(scheme: str,mode: str,base: Path) -> dict:
    mode='light' if mode.strip()=='light' else 'dark'
    name=scheme.removeprefix('community ').strip()
    colors=dict(LIGHT if mode=='light' else DARK);fallback=True
    if scheme.startswith('community ') and name:
        path=base/(quote(name,safe='')+'.json')
        try:
            if path.stat().st_size>1024*1024:raise ValueError('Paleta grande demais')
            values=json.loads(path.read_text())[mode]
            for key in colors:
                value=values.get(key)
                if isinstance(value,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',value):colors[key]=value
            fallback=False
        except (OSError,ValueError,KeyError,TypeError):pass
    return {'name':name or 'indisponível','mode':mode,'colors':colors,'fallback':fallback}


def current() -> dict:
    try:
        def query(command: str) -> str:
            return subprocess.check_output(['hyprbar','msg',command],text=True,stderr=subprocess.DEVNULL,timeout=2).strip()
        scheme=query('color-scheme-get');mode=query('theme-mode-get')
    except (OSError,subprocess.SubprocessError):scheme='';mode='dark'
    base=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'hyprbar/community-palettes'
    return resolve(scheme,mode,base)
