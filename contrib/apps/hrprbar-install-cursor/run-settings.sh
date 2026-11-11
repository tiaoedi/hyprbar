#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${PYTHON:-python3}
"$PYTHON" -c 'import tkinter; import PIL; import ctypes.util; assert ctypes.util.find_library("Xcursor"), "libXcursor não encontrada"' || {
    printf '%s\n' 'Dependências ausentes: use Python 3.10+ com Tkinter, Pillow e libXcursor. Nenhum pacote foi instalado.' >&2
    exit 1
}
exec "$PYTHON" "$ROOT/settings_home.py" "$@"
