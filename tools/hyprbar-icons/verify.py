#!/usr/bin/python3
"""Headless Rsvg/Cairo validation and isolated GTK lookups; never sets desktop theme."""
from pathlib import Path
import json
import math
import tempfile
import cairo
import gi
gi.require_version('Rsvg', '2.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Rsvg, Gtk

ROOT = Path(__file__).resolve().parent
THEME = ROOT / 'hyprbar'
SIZES = (16, 32, 64, 128)


def render(path: Path, size: int) -> cairo.ImageSurface:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    handle = Rsvg.Handle.new_from_file(str(path))
    viewport = Rsvg.Rectangle()
    viewport.x = viewport.y = 0
    viewport.width = viewport.height = size
    assert handle.render_document(cairo.Context(surface), viewport), path
    surface.flush()
    data = memoryview(surface.get_data()).cast('B')
    alpha = data[3::4]
    assert max(alpha) > 200, f'Blank render: {path} at {size}'
    assert min(alpha) == 0, f'Missing transparent margin: {path} at {size}'
    assert data[3] == 0, f'Corner must stay transparent: {path}'
    assert sum(a > 0 for a in alpha) > size*size*.2, f'Insufficient visible artwork: {path}'
    return surface


def label(ctx: cairo.Context, text: str, x: float, y: float, max_width: int) -> None:
    # Fonts are used only in preview annotations, never in SVG artwork.
    while ctx.text_extents(text).width > max_width and len(text)>3:
        text = text[:-2]+'…'
    ctx.move_to(x,y)
    ctx.show_text(text)


def verify() -> dict:
    manifest = json.loads((ROOT/'manifest.json').read_text())
    scratch = Path(tempfile.gettempdir())
    scratch.mkdir(parents=True, exist_ok=True)
    renders = Path(tempfile.mkdtemp(prefix='hyprbar-icons-render-',dir=scratch))
    previews = ROOT/'previews'
    previews.mkdir(exist_ok=True)
    icons = manifest['canonical']
    columns, cellw, cellh = 8, 166, 161
    width, height = columns*cellw, 86+math.ceil(len(icons)/columns)*cellh
    sheet = cairo.ImageSurface(cairo.FORMAT_ARGB32,width,height)
    ctx = cairo.Context(sheet)
    ctx.set_source_rgb(.075,.09,.13)
    ctx.paint()
    ctx.select_font_face('sans-serif',cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(26)
    ctx.set_source_rgb(.92,.95,1)
    label(ctx,'hyprbar / original semantic icons',26,38,width-52)
    ctx.set_font_size(12)
    ctx.select_font_face('sans-serif')
    ctx.set_source_rgb(.65,.72,.82)
    label(ctx,f'{len(icons)} originals · rounded tiles / blue folders / folded documents · no brand emblems',26,62,width-52)
    render_count = 0
    for i, icon in enumerate(icons):
        largest = None
        for size in SIZES:
            surface = render(THEME/icon['path'],size)
            output = renders/str(size)
            output.mkdir(exist_ok=True)
            surface.write_to_png(str(output/(icon['name']+'.png')))
            render_count += 1
            if size==128:
                largest=surface
        x,y = (i%columns)*cellw,86+(i//columns)*cellh
        ctx.set_source_surface(largest,x+(cellw-128)/2,y)
        ctx.paint()
        ctx.set_font_size(10)
        ctx.set_source_rgb(.81,.86,.94)
        label(ctx,icon['name'],x+10,y+142,cellw-20)
    preview = previews/'contact-sheet.png'
    sheet.write_to_png(str(preview))
    # A compact scale inspection strip for representative silhouettes.
    strip = cairo.ImageSurface(cairo.FORMAT_ARGB32,760,790)
    sc = cairo.Context(strip)
    sc.set_source_rgb(.94,.96,.98)
    sc.paint()
    sc.set_source_rgb(.16,.2,.27)
    sc.set_font_size(12)
    for col,size in enumerate(SIZES):
        label(sc,f'{size}px',225+col*115,22,110)
    examples = ['folder-documents','text-x-generic','hyprbar','bitwarden','org.gnome.Nautilus']
    for row,name in enumerate(examples):
        icon=next(r for r in icons if r['name']==name)
        sc.set_source_rgb(.16,.2,.27)
        sc.set_font_size(12)
        label(sc,name,12,30+row*150+76,190)
        for col,size in enumerate(SIZES):
            surface=render(THEME/icon['path'],size)
            sc.set_source_surface(surface,225+col*115,30+row*150+(140-size)/2)
            sc.paint()
    strip.write_to_png(str(previews/'size-check.png'))
    icon_theme = Gtk.IconTheme.new()
    # Explicit search path; no default display, settings, caches, or real apps changed.
    icon_theme.set_search_path([str(ROOT),'/usr/share/icons'])
    icon_theme.set_theme_name('hyprbar')
    lookup_count = 0
    for icon in icons+manifest['aliases']:
        for size in SIZES:
            paintable = icon_theme.lookup_icon(icon['name'],[],size,1,Gtk.TextDirection.NONE,Gtk.IconLookupFlags.FORCE_REGULAR)
            source = paintable.get_file()
            assert source is not None, f'GTK failed lookup: {icon["name"]}'
            actual=Path(source.get_path())
            assert actual.resolve()==(THEME/icon['path']).resolve(), f'Fallback unexpectedly used: {icon["name"]} {actual}'
            lookup_count += 1
    symbolic = {}
    for name in ('folder-symbolic','user-trash-symbolic','go-next-symbolic','network-wireless-symbolic'):
        paintable=icon_theme.lookup_icon(name,[],16,1,Gtk.TextDirection.NONE,Gtk.IconLookupFlags.FORCE_SYMBOLIC)
        source=paintable.get_file()
        assert source is not None, f'Symbolic fallback missing: {name}'
        filename=source.get_path() or source.get_uri()
        assert filename.endswith('/'+name+'.svg') and '/Adwaita/' in filename, f'Unexpected symbolic source: {name} {filename}'
        assert str(THEME) not in filename, f'Local symbolic override: {name}'
        symbolic[name]=filename
    report={**manifest['totals'],'sizes':list(SIZES),'render_count':render_count,'lookup_count':lookup_count,'symbolic_inherited':True,'symbolic_sources':symbolic,'render_directory':str(renders),'preview':str(preview),'size_preview':str(previews/'size-check.png'),'transparent_corners':True}
    (ROOT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    verify()
