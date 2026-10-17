"""Build a renamed OFL derivative; does not copy or imitate Apple's font files."""
import argparse
import shutil
from pathlib import Path
from fontTools.ttLib import TTFont

SOURCE = Path('/usr/share/fonts/adwaita-sans-fonts')
LICENSE = Path('/usr/share/licenses/adwaita-sans-fonts/LICENSE')

def build(output):
    output.mkdir(parents=True, exist_ok=True)
    for style in ('Regular','Italic'):
        font = TTFont(SOURCE/f'AdwaitaSans-{style}.ttf', recalcTimestamp=False, recalcBBoxes=False)
        names = font['name']
        psname = 'Hyprbar' + ('-Italic' if style == 'Italic' else '')
        replacements = {
            1:'Hyprbar', 3:f'Hyprbar-1.000-{style}',
            4:'Hyprbar' + (' Italic' if style=='Italic' else ''),
            6:psname, 16:'Hyprbar', 17:style, 21:'Hyprbar',22:style,
            25:'Hyprbar' + ('Italic' if style=='Italic' else ''),
            10:'Hyprbar is a renamed derivative of Adwaita Sans (based on Inter). Glyph outlines and variable axes are unchanged. This is not Apple San Francisco.',
        }
        # Preserve all original copyright, designer and OFL license records.
        for record in list(names.names):
            if record.nameID in replacements:
                names.setName(replacements[record.nameID],record.nameID,record.platformID,record.platEncID,record.langID)
            elif record.nameID >= 256:
                text=record.toUnicode()
                new=text.replace('Adwaita Sans','Hyprbar').replace('AdwaitaSans','Hyprbar').replace('InterVariable','Hyprbar')
                if new != text:
                    names.setName(new,record.nameID,record.platformID,record.platEncID,record.langID)
        # Supply consistent Windows and Unicode naming even if absent upstream.
        for nid,text in replacements.items():
            names.setName(text,nid,3,1,0x409)
            names.setName(text,nid,0,4,0)
        target=output/f'Hyprbar-{style}.ttf'
        font.save(target)
        print(target)
    shutil.copy2(LICENSE,output/'OFL.txt')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    build(parser.parse_args().output)
