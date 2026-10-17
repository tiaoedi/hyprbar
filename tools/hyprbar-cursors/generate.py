#!/usr/bin/env python3
"""Generate original Hyprbar Xcursor and Hyprcursor themes."""
from __future__ import annotations
import argparse, math, struct, subprocess, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
THEME = ROOT / "hyprbar"
CURSORS = THEME / "cursors"
SIZE = 48

# Original, monochrome macOS-inspired geometry: white fill, charcoal outline,
# and a restrained Hyprbar-blue accent. No Apple marks or copied artwork.
SVG = {
"default": ('<path d="M8 4 L8 39 L17 30 L23 43 L29 40 L23 27 L36 26 Z" fill="#fff" stroke="#202633" stroke-width="2.4" stroke-linejoin="round"/><path d="M12 10 L31 24 L21 25 L17 32 Z" fill="#dce8ff"/>', 8, 4),
"hand": ('<path d="M16 25V12a3 3 0 0 1 6 0v10-13a3 3 0 0 1 6 0v13-10a3 3 0 0 1 6 0v12-7a3 3 0 0 1 6 0v14c0 8-5 13-13 13h-3c-5 0-8-3-11-7l-5-7a3 3 0 0 1 5-4z" fill="#fff" stroke="#202633" stroke-width="2.2" stroke-linejoin="round"/><path d="M20 34h17" stroke="#5b8def" stroke-width="2.5" stroke-linecap="round"/>', 22, 22),
"text": ('<path d="M11 10h26M24 10v28M11 38h26" fill="none" stroke="#202633" stroke-width="3" stroke-linecap="round"/><path d="M16 13h16" stroke="#fff" stroke-width="1.2"/>', 24, 24),
"crosshair": ('<circle cx="24" cy="24" r="13" fill="#fff" fill-opacity=".9" stroke="#202633" stroke-width="2.4"/><path d="M24 3v13m0 16v13M3 24h13m16 0h13" stroke="#202633" stroke-width="2.5" stroke-linecap="round"/><circle cx="24" cy="24" r="3" fill="#5b8def"/>', 24, 24),
"wait": ('<circle cx="24" cy="24" r="17" fill="#fff" stroke="#202633" stroke-width="2.5"/><path d="M24 7a17 17 0 0 1 16 11" fill="none" stroke="#5b8def" stroke-width="5" stroke-linecap="round"/><circle cx="24" cy="24" r="3" fill="#202633"/>', 24, 24),
"progress": ('<path d="M8 4 L8 39 L17 30 L23 43 L29 40 L23 27 L36 26 Z" fill="#fff" stroke="#202633" stroke-width="2.4" stroke-linejoin="round"/><path d="M12 10 L31 24 L21 25 L17 32 Z" fill="#dce8ff"/><circle cx="37" cy="38" r="8" fill="#fff" stroke="#202633" stroke-width="2"/><path d="M37 33v5l3 2" fill="none" stroke="#5b8def" stroke-width="2" stroke-linecap="round"/>', 8, 4),
"move": ('<path d="M24 4v40M4 24h40M24 4l-6 7m6-7 6 7M44 24l-7-6m7 6-7 6M24 44l-6-7m6 7 6-7M4 24l7-6m-7 6 7 6" fill="none" stroke="#202633" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="24" cy="24" r="4" fill="#5b8def" stroke="#fff" stroke-width="1.5"/>', 24, 24),
"not-allowed": ('<circle cx="24" cy="24" r="17" fill="#fff" stroke="#202633" stroke-width="2.5"/><path d="M12 12l24 24" stroke="#e25555" stroke-width="4" stroke-linecap="round"/>', 24, 24),
"help": ('<circle cx="24" cy="24" r="18" fill="#fff" stroke="#202633" stroke-width="2.4"/><path d="M18 18a6 6 0 1 1 9 5c-3 2-3 3-3 6" fill="none" stroke="#5b8def" stroke-width="3.5" stroke-linecap="round"/><circle cx="24" cy="35" r="2" fill="#202633"/>', 24, 24),
"copy": ('<path d="M8 4L8 35l8-8 6 13 5-2-6-13h11z" fill="#fff" stroke="#202633" stroke-width="2.2" stroke-linejoin="round"/><rect x="27" y="27" width="15" height="15" rx="3" fill="#dce8ff" stroke="#202633" stroke-width="2"/><path d="M31 34l3 3 5-6" fill="none" stroke="#5b8def" stroke-width="2"/>', 8, 4),
"alias": ('<path d="M8 4L8 35l8-8 6 13 5-2-6-13h11z" fill="#fff" stroke="#202633" stroke-width="2.2" stroke-linejoin="round"/><path d="M31 29h10v10M41 29l-9 10" fill="none" stroke="#5b8def" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>', 8, 4),
"context-menu": ('<path d="M8 4L8 39l9-9 6 13 6-3-6-12 13-1z" fill="#fff" stroke="#202633" stroke-width="2.4" stroke-linejoin="round"/><circle cx="39" cy="35" r="2" fill="#5b8def"/><circle cx="39" cy="41" r="2" fill="#5b8def"/>', 8, 4),
"grab": ('<path d="M16 25V12a3 3 0 0 1 6 0v10-13a3 3 0 0 1 6 0v13-10a3 3 0 0 1 6 0v12-7a3 3 0 0 1 6 0v14c0 8-5 13-13 13h-3c-5 0-8-3-11-7l-5-7a3 3 0 0 1 5-4z" fill="#fff" stroke="#202633" stroke-width="2.2" stroke-linejoin="round"/><path d="M21 35h14" stroke="#5b8def" stroke-width="2.5" stroke-linecap="round"/>', 22, 22),
"grabbing": ('<path d="M13 24l4-13a3 3 0 0 1 6 2l-2 9 4-14a3 3 0 0 1 6 2l-3 13 5-11a3 3 0 0 1 6 3l-5 13 5-5a3 3 0 0 1 5 4l-8 13c-4 6-10 7-17 4l-3-2c-4-2-6-6-7-11l-2-8a3 3 0 0 1 6-2z" fill="#fff" stroke="#202633" stroke-width="2.2" stroke-linejoin="round"/><path d="M19 35h14" stroke="#5b8def" stroke-width="2.5" stroke-linecap="round"/>', 22, 22),
"ew-resize": ('<path d="M4 24h40M4 24l8-7m-8 7 8 7M44 24l-8-7m8 7-8 7" fill="none" stroke="#202633" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="20" y="19" width="8" height="10" rx="3" fill="#5b8def" stroke="#fff" stroke-width="1.5"/>', 24, 24),
"ns-resize": ('<path d="M24 4v40M24 4l-7 8m7-8 7 8M24 44l-7-8m7 8 7-8" fill="none" stroke="#202633" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><rect x="19" y="20" width="10" height="8" rx="3" fill="#5b8def" stroke="#fff" stroke-width="1.5"/>', 24, 24),
"nwse-resize": ('<path d="M8 8l32 32M8 8v10m0-10h10m22 32V30m0 10H30" fill="none" stroke="#202633" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="24" cy="24" r="4" fill="#5b8def" stroke="#fff" stroke-width="1.5"/>', 24, 24),
"nesw-resize": ('<path d="M40 8L8 40m32-32H30m10 0v10M8 40h10M8 40V30" fill="none" stroke="#202633" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="24" cy="24" r="4" fill="#5b8def" stroke="#fff" stroke-width="1.5"/>', 24, 24),
"col-resize": ('<path d="M5 24h38M5 24l8-7m-8 7 8 7M43 24l-8-7m8 7-8 7" fill="none" stroke="#202633" stroke-width="3" stroke-linecap="round"/><rect x="18" y="19" width="12" height="10" rx="3" fill="#dce8ff" stroke="#5b8def" stroke-width="2"/>', 24, 24),
"row-resize": ('<path d="M24 5v38M24 5l-7 8m7-8 7 8M24 43l-7-8m7 8 7-8" fill="none" stroke="#202633" stroke-width="3" stroke-linecap="round"/><rect x="19" y="18" width="10" height="12" rx="3" fill="#dce8ff" stroke="#5b8def" stroke-width="2"/>', 24, 24),
"zoom-in": ('<circle cx="20" cy="20" r="12" fill="#fff" stroke="#202633" stroke-width="2.5"/><path d="M29 29l12 12M20 14v12m-6-6h12" fill="none" stroke="#5b8def" stroke-width="3" stroke-linecap="round"/>', 20, 20),
"zoom-out": ('<circle cx="20" cy="20" r="12" fill="#fff" stroke="#202633" stroke-width="2.5"/><path d="M29 29l12 12M14 20h12" fill="none" stroke="#5b8def" stroke-width="3" stroke-linecap="round"/>', 20, 20),
}
ALIASES = {
"left_ptr":"default", "arrow":"default", "top_left_arrow":"default", "pointer":"hand", "e-resize":"ew-resize", "w-resize":"ew-resize", "h-resize":"ew-resize", "v-resize":"ns-resize", "n-resize":"ns-resize", "s-resize":"ns-resize", "ne-resize":"nesw-resize", "sw-resize":"nesw-resize", "nw-resize":"nwse-resize", "se-resize":"nwse-resize", "size_hor":"ew-resize", "size_ver":"ns-resize", "size_fdiag":"nwse-resize", "size_bdiag":"nesw-resize", "dnd-copy":"copy", "dnd-move":"move", "dnd-none":"not-allowed", "cross":"crosshair", "xterm":"text", "ibeam":"text", "watch":"wait", "left_ptr_watch":"progress", "fleur":"move", "hand1":"hand", "hand2":"hand", "grabbing":"grabbing", "openhand":"grab", "closedhand":"grabbing", "forbidden":"not-allowed", "whats_this":"help", "question_arrow":"help", "copy":"copy", "link":"alias", "vertical-text":"text", "cell":"crosshair", "all-scroll":"move", "no-drop":"not-allowed", "not-allowed":"not-allowed", "context-menu":"context-menu", "zoom-in":"zoom-in", "zoom-out":"zoom-out"
}

def render_svg(body: str, path: Path) -> None:
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">{body}</svg>\n')

def xcursor_chunk(name: str, svg: str, hotx: int, hoty: int, out: Path) -> None:
    sizes = (24, 32, 48)
    chunks = []
    with tempfile.TemporaryDirectory() as td:
        svg_path, png_path = Path(td)/'cursor.svg', Path(td)/'cursor.png'
        render_svg(svg, svg_path)
        for size in sizes:
            subprocess.run(['magick', '-background', 'none', str(svg_path), '-resize', f'{size}x{size}!', '-depth', '8', f'PNG32:{png_path}'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            rgba = subprocess.check_output(['magick', str(png_path), '-depth', '8', 'rgba:-'])
            if len(rgba) != size*size*4:
                raise ValueError(f'bad render: {name} ({len(rgba)})')
            pixels = bytearray()
            for i in range(0, len(rgba), 4):
                r,g,b,a = rgba[i:i+4]
                # Xcursor stores premultiplied ARGB, unlike PNG's straight RGBA.
                r,g,b = ((channel*a + 127)//255 for channel in (r,g,b))
                pixels.extend(struct.pack('<I', (a<<24)|(r<<16)|(g<<8)|b))
            hx, hy = round(hotx*size/SIZE), round(hoty*size/SIZE)
            chunks.append(struct.pack('<IIIIIIIII', 36, 0xfffd0002, size, 1, size, size, hx, hy, 0) + pixels)
    offset = 16 + 12*len(sizes)
    toc = bytearray()
    for size, chunk in zip(sizes, chunks):
        toc.extend(struct.pack('<III', 0xfffd0002, size, offset))
        offset += len(chunk)
    out.write_bytes(struct.pack('<IIII', 0x72756358, 16, 1, len(sizes)) + toc + b''.join(chunks))

def build_hyprcursor(theme: Path) -> None:
    """Write Hyprcursor's compiled theme: manifest plus one ZIP per shape."""
    folder = theme / "hyprcursors"
    folder.mkdir(parents=True, exist_ok=True)
    (theme / "manifest.hl").write_text(chr(10).join([
        "name = hyprbar",
        "description = Original modern cursors without logos",
        "version = 1.0",
        "cursors_directory = hyprcursors",
    ]) + chr(10))
    for name, (body, hotx, hoty) in SVG.items():
        overrides = sorted(alias for alias, target in ALIASES.items()
                           if target == name and alias != name)
        meta = [
            "resize_algorithm = bilinear",
            f"hotspot_x = {hotx / SIZE:.6f}",
            f"hotspot_y = {hoty / SIZE:.6f}",
        ]
        meta.extend(f"define_override = {alias}" for alias in overrides)
        meta.append(f"define_size = {SIZE}, image.svg")
        image = f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">{body}</svg>'
        with zipfile.ZipFile(folder / name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("meta.hl", chr(10).join(meta) + chr(10))
            archive.writestr("image.svg", image)

def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument('--output', type=Path, default=THEME); a=ap.parse_args()
    theme=a.output.resolve(); cursors=theme/'cursors'; cursors.mkdir(parents=True, exist_ok=True)
    for n,(svg,hx,hy) in SVG.items():
        image_path=cursors/n
        if image_path.is_symlink(): image_path.unlink()
        xcursor_chunk(n,svg,hx,hy,image_path)
    for alias,target in ALIASES.items():
        if alias in SVG: continue
        p=cursors/alias
        if p.exists() or p.is_symlink(): p.unlink()
        p.symlink_to(target)
    build_hyprcursor(theme)
    (theme/'index.theme').write_text('[Icon Theme]\nName=hyprbar\nComment=Modern, original macOS-inspired cursor theme\nInherits=Adwaita\n')
    print(f'generated {len(SVG)} Xcursor images and {sum(alias not in SVG for alias in ALIASES)} aliases in {theme}')
if __name__=='__main__': main()
