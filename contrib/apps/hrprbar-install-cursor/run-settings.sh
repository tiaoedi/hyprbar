#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

check_python() {
    [ -x "$1" ] && "$1" -c 'import sys, tkinter; from PIL import Image, ImageTk, ImageDraw; import ctypes.util; assert sys.version_info >= (3, 10); assert ctypes.util.find_library("Xcursor"), "libXcursor não encontrada"' >/dev/null 2>&1
}

if [ -n "${PYTHON-}" ]; then
    if ! check_python "$PYTHON"; then
        printf '%s\n' "Interpretador incompatível: $PYTHON (requer Python 3.10+, Tkinter, Pillow com ImageTk e libXcursor)." >&2
        exit 1
    fi
else
    PYTHON=''
    for candidate in /usr/bin/python3 "$(command -v python3 2>/dev/null || true)" "$HOME"/.hermes/installs/*/environments/*/venv/bin/python3; do
        if check_python "$candidate"; then
            PYTHON=$candidate
            break
        fi
    done
    if [ -z "$PYTHON" ]; then
        printf '%s\n' 'Nenhum Python compatível encontrado: requer Python 3.10+, Tkinter, Pillow com ImageTk e libXcursor.' >&2
        exit 1
    fi
fi

exec "$PYTHON" "$ROOT/settings_home.py" "$@"
