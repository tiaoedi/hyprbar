#!/usr/bin/python3
"""Generate original, self-contained hyprbar artwork and local symlink aliases.
No third-party artwork, network access, fonts, or installed-theme changes.
"""
from pathlib import Path
import json
import os

ROOT = Path(__file__).resolve().parent
THEME = ROOT / 'hyprbar'

# Deliberately semantic, independently constructed line art, not brand logos.
GLYPHS = {
'home': '<path d="m36 61 28-24 28 24M43 59v32h16V73h11v18h15V59"/>',
'document': '<path d="M46 35h25l14 15v43H46zM70 36v16h14M55 64h20M55 75h20M55 85h13"/>',
'download': '<path d="M64 35v41m-15-15 15 15 15-15M40 81v12h48V81"/>',
'music': '<path d="M57 83V43l29-6v39M57 53l29-6"/><ellipse cx="47" cy="85" rx="10" ry="7" fill="currentColor" stroke="none"/><ellipse cx="76" cy="78" rx="10" ry="7" fill="currentColor" stroke="none"/>',
'image': '<rect x="35" y="40" width="58" height="47" rx="6"/><circle cx="75" cy="53" r="5"/><path d="m38 82 16-21 13 15 9-9 14 16"/>',
'video': '<rect x="33" y="42" width="43" height="44" rx="8"/><path d="m77 57 18-10v35L77 72z"/>',
'desktop': '<rect x="32" y="36" width="64" height="45" rx="6"/><path d="M64 82v12M49 95h30"/>',
'grid': '<rect x="37" y="37" width="22" height="22" rx="4"/><rect x="69" y="37" width="22" height="22" rx="4"/><rect x="37" y="69" width="22" height="22" rx="4"/><rect x="69" y="69" width="22" height="22" rx="4"/>',
'people': '<circle cx="54" cy="51" r="10"/><path d="M34 88v-6a20 20 0 0 1 40 0v6M78 42a10 10 0 0 1 0 20M84 71q12 3 12 17"/>',
'sliders': '<path d="M37 45h54M37 65h54M37 85h54"/><rect x="48" y="38" width="9" height="14" rx="3" fill="currentColor"/><rect x="73" y="58" width="9" height="14" rx="3" fill="currentColor"/><rect x="53" y="78" width="9" height="14" rx="3" fill="currentColor"/>',
'code': '<path d="m49 45-20 19 20 19m30-38 20 19-20 19M70 37 58 91"/>',
'folder': '<path d="M34 47h24l7 9h29v32H34z"/>',
'trash': '<path d="M40 47h48M54 38h20l4 9M44 48l4 46h32l4-46M57 58v25M71 58v25"/>',
'trash-full': '<path d="m39 45 48-7M51 39l3-10 19-3 5 8M44 49l4 45h32l4-48M57 58v25M71 58v25"/><path d="m54 50 9 9 10-8"/>',
'disk': '<rect x="33" y="39" width="62" height="51" rx="8"/><path d="M34 74h60M77 82h5"/><circle cx="47" cy="82" r="2" fill="currentColor"/>',
'usb': '<path d="M53 44V30h22v14M53 37h22"/><rect x="46" y="44" width="36" height="52" rx="10"/><path d="M64 57v24m-7-6 7 7 7-7"/>',
'network': '<rect x="51" y="31" width="26" height="23" rx="4"/><path d="M64 54v17M39 80v-9h50v9"/><rect x="28" y="80" width="23" height="17" rx="3"/><rect x="77" y="80" width="23" height="17" rx="3"/>',
'phone': '<rect x="46" y="29" width="36" height="70" rx="9"/><path d="M58 37h12M61 90h6"/>',
'printer': '<path d="M45 53V32h38v21M44 80H33V54h62v26H84M44 69h40v28H44zM55 80h18M55 88h18"/><circle cx="84" cy="62" r="2"/>',
'headphones': '<path d="M36 70v-9a28 28 0 0 1 56 0v9"/><rect x="32" y="64" width="14" height="26" rx="6"/><rect x="82" y="64" width="14" height="26" rx="6"/>',
'archive': '<rect x="35" y="38" width="58" height="54" rx="6"/><path d="M35 53h58M59 39v14M69 39v14M58 65h12v13H58z"/>',
'pdf': '<path d="M44 86V43h15a12 12 0 0 1 0 24H44M73 44h17M73 44v42M73 63h14"/>',
'sheet': '<rect x="34" y="36" width="60" height="56" rx="5"/><path d="M34 51h60M34 66h60M34 80h60M53 37v54M74 37v54"/>',
'presentation': '<rect x="31" y="35" width="66" height="45" rx="5"/><path d="M64 81v15m0-8-16 10m16-10 16 10M44 66V57m13 9V48m13 18V55m13 11V43"/>',
'draw': '<path d="m40 81 37-43 12 10-37 43-16 5zM70 46l12 10M40 81l12 10"/><circle cx="42" cy="43" r="9"/>',
'play': '<path d="m51 37 42 27-42 27z" fill="currentColor" stroke="none"/>',
'browser': '<rect x="29" y="33" width="70" height="61" rx="12"/><path d="M30 49h68M40 41h1m8 0h1"/><circle cx="64" cy="71" r="16"/><path d="M48 71h32M64 55q-12 16 0 32 12-16 0-32"/>',
'shield': '<path d="m64 31 27 11v21q-2 23-27 35-25-12-27-35V42zM51 63l9 10 18-23"/>',
'orbit': '<circle cx="64" cy="64" r="16"/><ellipse cx="64" cy="64" rx="39" ry="18" transform="rotate(-34 64 64)"/><path d="m80 31 9 3-1 10"/>',
'fox': '<path d="m39 35 18 16h17l15-16 6 31q-2 28-31 31-29-3-31-31zM46 63l10 7m26-7-10 7m-15 9 7 6 7-6"/>',
'wave': '<path d="M31 67h10l8-23 14 42 13-51 12 32h10"/>',
'capture': '<path d="M35 52V36h17M76 36h17v16M93 76v17H76M52 93H35V76"/><circle cx="64" cy="64" r="17"/><circle cx="64" cy="64" r="7" fill="currentColor" stroke="none"/>',
'brush': '<path d="m56 68 27-36 12 10-32 33zM55 71q-17 0-16 17l-7 7q31 5 31-20"/>',
'chat': '<path d="M34 41h60v39H60L43 95V80h-9z"/><path d="M47 55h34M47 66h24"/>',
'voice': '<path d="M36 49q28-22 56 0v36L78 79H50l-14 6zM49 61v8M64 57v16M79 61v8"/>',
'lock': '<rect x="39" y="57" width="50" height="39" rx="8"/><path d="M48 57V45a16 16 0 0 1 32 0v12M64 72v10"/>',
'calculator': '<rect x="39" y="29" width="50" height="70" rx="9"/><path d="M49 40h30v14H49zM50 65h4m12 0h12M50 77h4m12 0h12M50 89h4m12 0h12"/>',
'calendar': '<rect x="33" y="38" width="62" height="57" rx="9"/><path d="M33 55h62M48 31v15M80 31v15M47 68h6m12 0h6m12 0h1M47 82h6m12 0h6"/>',
'bag': '<path d="M39 48h50l7 48H32zM51 49V40a13 13 0 0 1 26 0v9M53 71l9 10 17-20"/>',
'bar': '<rect x="29" y="37" width="70" height="55" rx="11"/><path d="M30 51h68M41 44h5m8 0h5M43 65v14m12-9v9m12-18v18m12-13v13m9-6v6"/>',
'compass': '<circle cx="64" cy="64" r="30"/><path d="m55 53 23-7-6 25-23 10zM55 53l17 18"/>',
'bulb': '<path d="M52 78q0-8-8-16a25 25 0 1 1 40 0q-8 8-8 16zM53 87h22M57 95h14M64 78V56m-8 0 8 7 8-7"/>',
'clock': '<circle cx="64" cy="64" r="30"/><path d="M64 43v23l16 10"/>',
'search': '<circle cx="57" cy="56" r="22"/><path d="m74 73 20 21"/>',
}

# name, family, glyph, upper/lower palette, aliases. All names are case-sensitive.
RECORDS = []
def add(name: str, family: str, glyph: str, colors: tuple, aliases: str = '') -> None:
    RECORDS.append(dict(name=name, family=family, glyph=glyph, colors=colors, aliases=aliases.split()))

for name, glyph, aliases in [
('folder','folder','inode-directory'), ('user-home','home','folder-home'),
('folder-documents','document',''), ('folder-download','download','folder-downloads'),
('folder-music','music',''), ('folder-pictures','image','folder-images'),
('folder-videos','video','folder-video'), ('user-desktop','desktop','folder-desktop'),
('folder-templates','grid',''), ('folder-publicshare','people','folder-public'),
('folder-config','sliders','folder-settings'), ('folder-code','code','folder-development'),
('folder-remote','network','folder-network')]:
    add(name, 'places', glyph, ('#70ceff','#1976df'), aliases)
for name,glyph,aliases in [
('user-trash','trash','user-trash-empty'), ('user-trash-full','trash-full',''),
('drive-harddisk','disk','drive-harddisk-system drive-harddisk-solidstate'),
('drive-removable-media','disk','media-removable'), ('drive-removable-media-usb','usb','drive-harddisk-usb drive-removable-usb'),
('network-workgroup','network','network-server network-wired'), ('computer','desktop','computer-laptop'),
('phone','phone','smartphone'), ('printer','printer','printer-network'), ('audio-headphones','headphones','audio-headset')]:
    palette = ('#addcd8','#508f91') if name == 'drive-removable-media' else ('#b6c9dd','#5d7898')
    add(name, 'devices' if name not in ('user-trash','user-trash-full','network-workgroup') else 'places', glyph, palette, aliases)
for name,glyph,colors,aliases in [
('text-x-generic','document',('#f4f7ff','#d8e2f3'),'text-plain text-x-readme'),
('application-pdf','pdf',('#ff7b8b','#dd324a'),''),
('image-x-generic','image',('#9addbc','#36a77a'),'image-png image-jpeg image-svg+xml'),
('audio-x-generic','music',('#ddadff','#9156dc'),'audio-mpeg audio-x-wav'),
('video-x-generic','play',('#9db5ff','#5968dc'),'video-mp4 video-webm'),
('package-x-generic','archive',('#e6bd88','#b77b3d'),'application-x-archive application-zip application-x-compressed-tar application-x-7z-compressed application-x-rar'),
('text-x-script','code',('#98d9ef','#3597bc'),'text-x-python text-x-shellscript text-html application-javascript text-css text-x-csrc'),
('x-office-spreadsheet','sheet',('#8dd4ae','#3b9d6a'),'application-vnd.oasis.opendocument.spreadsheet'),
('x-office-presentation','presentation',('#ffc190','#e07844'),'application-vnd.oasis.opendocument.presentation'),
('x-office-document','document',('#9bc3ff','#4a82d8'),'application-vnd.oasis.opendocument.text'),
('application-x-executable','grid',('#c7c3e4','#8782b8'),'application-x-sharedlib')]:
    add(name,'mimetypes',glyph,colors,aliases)
for name,glyph,colors,aliases in [
('org.gnome.Nautilus','folder',('#83d7ff','#2588ef'),'org.gnome.nautilus nautilus system-file-manager file-manager'),
('hyprbar','bar',('#a899ff','#6454d9'),''),
('google-chrome','browser',('#77cce9','#2874b7'),'google-chrome-stable chromium chromium-browser org.chromium.Chromium'),
('brave-browser','shield',('#ffba7c','#ed6c3b'),'brave com.brave.Browser'),
('firefox','fox',('#cc9afd','#7757d4'),'org.mozilla.firefox firefox-esr'),
('kitty','code',('#61758d','#243448'),'utilities-terminal terminal org.gnome.Terminal Alacritty foot'),
('code','code',('#77ceef','#2577b5'),'vscode visual-studio-code com.visualstudio.code code-oss VSCodium codium'),
('vlc','play',('#ffbd71','#e98436'),'org.videolan.VLC'),
('com.obsproject.Studio','capture',('#667083','#272c3a'),'obs obs-studio'),
('gimp','brush',('#a997c7','#675583'),'org.gimp.GIMP'),
('libreoffice-writer','document',('#91c6ff','#3779cc'),'writer'),
('libreoffice-calc','sheet',('#91deb6','#31946a'),'calc'),
('libreoffice-impress','presentation',('#ffc48a','#dc7741'),'impress'),
('libreoffice-draw','draw',('#f7d57f','#ca9c32'),'draw'),
('libreoffice-startcenter','grid',('#b4c5d9','#657f9e'),'libreoffice org.libreoffice.LibreOffice'),
('org.telegram.desktop','chat',('#83d7f8','#3192c6'),'telegram telegram-desktop'),
('discord','voice',('#b7b4fc','#7069d6'),'com.discordapp.Discord'),
('bitwarden','lock',('#90b7ff','#477ce0'),'com.bitwarden.desktop brave-gneipglanmgpdhiohiogfnhdpoaafoob-Default'),
('org.pulseaudio.pavucontrol','sliders',('#afbdd6','#657b9e'),'pavucontrol multimedia-volume-control'),
('accessories-calculator','calculator',('#90c6d7','#487f96'),'org.gnome.Calculator gnome-calculator calculator'),
('x-office-calendar','calendar',('#ffabaf','#d76878'),'org.gnome.Calendar calendar'),
('preferences-system','sliders',('#afbcd1','#647b9a'),'org.gnome.Settings gnome-control-center systemsettings settings'),
('org.gnome.Software','bag',('#8bcddd','#3b88aa'),'system-software-install software-center'),
('accessories-text-editor','document',('#b8dbf9','#6999c6'),'org.gnome.TextEditor org.gnome.gedit gedit'),
('accessories-screenshot','capture',('#c3b1ef','#8971be'),'org.gnome.Screenshot'),
('accessories-clock','clock',('#92d7d4','#429d99'),'org.gnome.clocks'),
('help-browser','bulb',('#efcc8a','#c49644'),'org.gnome.Yelp'),
('system-search','search',('#9dd2f7','#4e94c7'),'org.gnome.Search')]:
    add(name,'apps',glyph,colors,aliases)


def svg(record: dict) -> str:
    hi,lo = record['colors']
    glyph = GLYPHS[record['glyph']]
    defs = f'''<defs><linearGradient id="body" x1="0" y1="0" x2="0.3" y2="1"><stop stop-color="{hi}"/><stop offset="1" stop-color="{lo}"/></linearGradient><linearGradient id="shine" x2="0" y2="1"><stop stop-color="#fff" stop-opacity=".36"/><stop offset=".65" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'''
    is_folder = record['family']=='places' and record['name'] not in ('user-trash','user-trash-full','network-workgroup')
    if is_folder:
        base = '''<path d="M10 43V31q0-10 10-10h29l12 12h47q10 0 10 10v54q0 12-12 12H22q-12 0-12-12z" fill="#246ab3" opacity=".20" transform="translate(0 4)"/><path d="M10 43V31q0-10 10-10h29l12 12h47q10 0 10 10v54H10z" fill="#429ce7"/><path d="M19 37h89v51H19z" fill="#e1f4ff"/><path d="M10 49q0-10 10-10h88q10 0 10 10v48q0 12-12 12H22q-12 0-12-12z" fill="url(#body)"/><path d="M21 40h86q10 0 10 10v8H11v-8q0-10 10-10z" fill="url(#shine)"/><path d="M22 41h84" stroke="#fff" stroke-opacity=".5" stroke-width="1.5"/>'''
        symbol = f'<g transform="translate(17 31) scale(.74)" color="#ecfaff" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">{glyph}</g>' if record['name']!='folder' else ''
    elif record['family']=='mimetypes':
        base = '''<path d="M31 13h45l23 23v70q0 9-9 9H40q-9 0-9-9z" fill="#203650" opacity=".14" transform="translate(0 3)"/><path d="M31 13h45l23 23v70q0 9-9 9H40q-9 0-9-9z" fill="#f8fbff"/><path d="M76 13v16q0 7 7 7h16" fill="#dbe4f2"/><rect x="31" y="45" width="68" height="59" rx="7" fill="url(#body)"/><path d="M39 107h45" stroke="#d9e2ef" stroke-width="2"/>'''
        color = '#55718c' if record['name']=='text-x-generic' else '#fff'
        symbol = f'<g transform="translate(17 25) scale(.74)" color="{color}" fill="none" stroke="currentColor" stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round">{glyph}</g>'
    else:
        base = '''<rect x="12" y="13" width="104" height="104" rx="25" fill="#142540" opacity=".12" transform="translate(0 3)"/><rect x="12" y="11" width="104" height="104" rx="25" fill="url(#body)"/><rect x="13" y="12" width="102" height="102" rx="24" fill="url(#shine)" stroke="#fff" stroke-opacity=".28" stroke-width="1.3"/><path d="M35 14h58" stroke="#fff" stroke-opacity=".25" stroke-width="1.4" stroke-linecap="round"/>'''
        symbol = f'<g transform="translate(0 -1)" color="#fff" fill="none" stroke="currentColor" stroke-width="4.3" stroke-linecap="round" stroke-linejoin="round">{glyph}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">{defs}{base}{symbol}</svg>\n'


def build() -> dict:
    THEME.mkdir(exist_ok=True)
    canonical, aliases = [], []
    occupied = set()
    for rec in RECORDS:
        directory = THEME / 'scalable' / rec['family']
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (rec['name']+'.svg')
        relative = str(path.relative_to(THEME))
        if relative in occupied:
            raise ValueError(f'Duplicate icon: {relative}')
        occupied.add(relative)
        path.write_text(svg(rec))
        canonical.append({'name':rec['name'], 'context':rec['family'], 'path':relative, 'glyph':rec['glyph'], 'palette':rec['colors']})
        for name in rec['aliases']:
            alias = directory / (name+'.svg')
            relalias = str(alias.relative_to(THEME))
            if relalias in occupied:
                raise ValueError(f'Duplicate alias: {relalias}')
            occupied.add(relalias)
            if alias.is_symlink():
                alias.unlink()
            elif alias.exists():
                raise ValueError(f'Refusing to overwrite non-symlink {alias}')
            alias.symlink_to(path.name)
            aliases.append({'name':name, 'path':relalias, 'target':relative})
    contexts = sorted({rec['family'] for rec in RECORDS})
    index = '[Icon Theme]\nName=hyprbar\nComment=Original rounded semantic icons; no brand emblems\nInherits=Adwaita,hicolor\nDirectories='+','.join('scalable/'+c for c in contexts)+'\n'
    for context in contexts:
        section_context = {'apps':'Applications','devices':'Devices','mimetypes':'MimeTypes','places':'Places'}[context]
        index += f'\n[scalable/{context}]\nSize=64\nMinSize=16\nMaxSize=512\nType=Scalable\nContext={section_context}\n'
    (THEME/'index.theme').write_text(index)
    (THEME/'LICENSE').write_text((ROOT/'LICENSE').read_text())
    manifest = {'theme':'hyprbar','license':'MIT','design':'original semantic glyphs; not official application branding','canonical':canonical,'aliases':aliases,'totals':{'canonical':len(canonical),'aliases':len(aliases),'svg_entries':len(canonical)+len(aliases)}}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest['totals']))
    return manifest

if __name__=='__main__':
    build()
