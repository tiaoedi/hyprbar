#!/usr/bin/env python3
"""Validate generated Hyprbar Xcursor files, aliases, and raster preview."""
from __future__ import annotations
import ctypes, pathlib, struct, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

ROOT=pathlib.Path(__file__).resolve().parent
THEME=ROOT/'hyprbar'
CUR=THEME/'cursors'
lib=ctypes.CDLL('libXcursor.so.1')
lib.XcursorFilenameLoadImages.argtypes=[ctypes.c_char_p,ctypes.c_int]
lib.XcursorFilenameLoadImages.restype=ctypes.c_void_p
lib.XcursorImagesDestroy.argtypes=[ctypes.c_void_p]
canonical=sorted(p for p in CUR.iterdir() if p.is_file() and not p.is_symlink())
errors=[]
manifest=THEME/'manifest.hl'
hypr=THEME/'hyprcursors'
expected_manifest={'name = hyprbar','cursors_directory = hyprcursors'}
if not manifest.is_file() or not expected_manifest.issubset(set(manifest.read_text().splitlines())):
    errors.append('Hyprcursor manifest is missing required theme fields')
hypr_files=sorted(p for p in hypr.iterdir() if p.is_file()) if hypr.is_dir() else []
if {p.name for p in hypr_files} != {p.name for p in canonical}:
    errors.append('Hyprcursor archive inventory does not match canonical Xcursor inventory')
for p in hypr_files:
    try:
        with zipfile.ZipFile(p) as archive:
            if set(archive.namelist()) != {'meta.hl','image.svg'}: raise ValueError('unexpected archive entries')
            meta=archive.read('meta.hl').decode()
            if 'resize_algorithm = bilinear' not in meta or 'define_size = 48, image.svg' not in meta:
                raise ValueError('required metadata missing')
            for key in ('hotspot_x','hotspot_y'):
                value=float(next(x.split('=',1)[1] for x in meta.splitlines() if x.startswith(key+' =')))
                if not 0 <= value <= 1: raise ValueError(f'{key} outside range')
            svg=archive.read('image.svg')
            root=ET.fromstring(svg)
            if not root.tag.endswith('svg') or b'<script' in svg or b'href=' in svg:
                raise ValueError('unsafe or invalid SVG')
    except Exception as e: errors.append(f'{p.name}: Hyprcursor archive: {e}')
thumbs=[]
for p in canonical:
    raw=p.read_bytes()
    try:
        magic,header,version,count=struct.unpack_from('<IIII',raw,0)
        if (magic,header,version,count)!=(0x72756358,16,1,3): raise ValueError('invalid Xcursor file header')
        expected_offset = 16 + 12*count
        for index, size in enumerate((24,32,48)):
            toc_type,nominal,offset=struct.unpack_from('<III',raw,16+12*index)
            if (toc_type,nominal,offset)!=(0xfffd0002,size,expected_offset): raise ValueError('invalid image table of contents')
            chunk_header,kind,subtype,image_version,w,h,hx,hy,delay=struct.unpack_from('<IIIIIIIII',raw,offset)
            if (chunk_header,kind,subtype,image_version,w,h)!=(36,0xfffd0002,size,1,size,size): raise ValueError('invalid image chunk')
            if not (0<=hx<w and 0<=hy<h): raise ValueError('hotspot outside image')
            expected_offset = offset+36+w*h*4
            for i in range(offset+36,expected_offset,4):
                argb=struct.unpack_from('<I',raw,i)[0]
                if max((argb>>16)&255,(argb>>8)&255,argb&255) > (argb>>24):
                    raise ValueError(f'non-premultiplied pixel at size {size}')
        if len(raw)!=expected_offset: raise ValueError('invalid image byte length')
        # The contact sheet displays the largest entry.
        _, _, offset = struct.unpack_from('<III',raw,16+12*(count-1))
        w = h = 48
        pixels=[]
        for i in range(offset+36,expected_offset,4):
            argb=struct.unpack_from('<I',raw,i)[0]
            alpha=(argb>>24)&255
            # Pillow expects straight alpha; undo Xcursor's premultiplication.
            rgb=tuple((channel*255 + alpha//2)//alpha if alpha else 0
                      for channel in ((argb>>16)&255,(argb>>8)&255,argb&255))
            pixels.append((*rgb,alpha))
        image=Image.new('RGBA',(w,h)); image.putdata(pixels)
        # Transparent canvas checker for a contact sheet, preserving source alpha.
        tile=Image.new('RGBA',(80,88),(239,242,247,255))
        tile.alpha_composite(image,(16,8))
        ImageDraw.Draw(tile).text((5,66),p.name[:12],fill=(30,38,51,255))
        thumbs.append(tile)
        ptr=lib.XcursorFilenameLoadImages(str(p).encode(),48)
        if not ptr: raise ValueError('libXcursor rejected cursor')
        lib.XcursorImagesDestroy(ptr)
    except Exception as e: errors.append(f'{p.name}: {e}')
for p in sorted(CUR.iterdir()):
    if p.is_symlink():
        if not p.exists(): errors.append(f'{p.name}: broken alias')
        elif p.resolve().parent!=CUR.resolve(): errors.append(f'{p.name}: alias escapes theme directory')
        elif not lib.XcursorFilenameLoadImages(str(p).encode(),48): errors.append(f'{p.name}: alias rejected by libXcursor')
if not canonical: errors.append('no canonical cursor images found')
cols=5; rows=(len(thumbs)+cols-1)//cols
sheet=Image.new('RGBA',(cols*80,rows*88),(250,251,253,255))
for i,t in enumerate(thumbs): sheet.alpha_composite(t,((i%cols)*80,(i//cols)*88))
preview=ROOT/'previews'/'contact-sheet.png'; preview.parent.mkdir(parents=True,exist_ok=True); sheet.save(preview)
print(f'canonical Xcursor files: {len(canonical)}')
print(f'aliases validated: {sum(p.is_symlink() for p in CUR.iterdir())}')
print(f'preview: {preview}')
if errors:
    print('\n'.join(errors),file=sys.stderr); raise SystemExit(1)
print('all Xcursor and Hyprcursor assets and aliases validated')
