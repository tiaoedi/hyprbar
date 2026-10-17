#!/usr/bin/env python3
"""Real Chrome/Brave checks. Only fresh scratch profiles and private CDP pipes.

Temporarily renders the extension's palette.css and restores its exact bytes.
No daily profile, browser UI, TCP debugging listener, or production config access.
"""
from __future__ import annotations

import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import tempfile
import time
from urllib.parse import parse_qs, urlparse
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(tempfile.gettempdir())


class Browser:
    def __init__(self, binary: str, work: Path) -> None:
        work.mkdir(parents=True)
        child_read, self.write = os.pipe()
        self.read, child_write = os.pipe()
        cr = fcntl.fcntl(child_read, fcntl.F_DUPFD, 10)
        cw = fcntl.fcntl(child_write, fcntl.F_DUPFD, 10)
        env = os.environ.copy()
        env.update(HOME=str(work), XDG_CONFIG_HOME=str(work / 'config'), XDG_CACHE_HOME=str(work / 'cache'),
                   XDG_STATE_HOME=str(work / 'state'), XDG_DATA_HOME=str(work / 'data'))
        args = [binary, '--headless=new', '--no-first-run', '--no-default-browser-check',
                '--disable-background-networking', '--disable-component-update', '--disable-sync',
                '--disable-gpu', '--remote-debugging-pipe', '--enable-unsafe-extension-debugging',
                '--window-size=1440,1000', f'--user-data-dir={work / "profile"}', 'about:blank']
        with (work / 'browser.log').open('wb') as log:
            self.process = subprocess.Popen(
                ['/bin/bash', '-c', f'exec "$@" 3<&{cr} 4>&{cw}', 'newtab-test', *args],
                env=env, pass_fds=(cr, cw), stdout=log, stderr=log, start_new_session=True)
        for fd in (child_read, child_write, cr, cw):
            os.close(fd)
        self.seq = 0
        self.buffer = b''
        self.events: list[dict] = []

    def rpc(self, method: str, params: dict | None = None, session: str | None = None) -> dict:
        self.seq += 1
        command = dict(id=self.seq, method=method, params=params or {})
        if session:
            command['sessionId'] = session
        os.write(self.write, json.dumps(command).encode() + b'\0')
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            while b'\0' in self.buffer:
                raw, self.buffer = self.buffer.split(b'\0', 1)
                if not raw:
                    continue
                message = json.loads(raw)
                if message.get('id') == self.seq:
                    if 'error' in message:
                        raise RuntimeError((method, message['error']))
                    return message.get('result', {})
                if 'method' in message:
                    self.events.append(message)
            ready, _, _ = select.select([self.read], [], [], max(0, deadline - time.monotonic()))
            if ready:
                chunk = os.read(self.read, 1048576)
                if not chunk:
                    raise RuntimeError('CDP pipe closed')
                self.buffer += chunk
        raise TimeoutError(method)

    def evaluate(self, expression: str, session: str) -> Any:
        result = self.rpc('Runtime.evaluate', dict(expression=expression, returnByValue=True), session)
        assert 'exceptionDetails' not in result, result
        return result['result'].get('value')

    def close(self) -> None:
        try:
            self.rpc('Browser.close')
        except (RuntimeError, TimeoutError, BrokenPipeError) as error:
            print('Browser.close:', error)
        for fd in (self.read, self.write):
            os.close(fd)
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=10)
        assert self.process.poll() is not None, 'test browser not reaped'


def wait_for(browser: Browser, expression: str, session: str) -> object:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        result = browser.evaluate(expression, session)
        if result:
            return result
        time.sleep(.1)
    raise AssertionError(f'timed out: {expression}')


def snapshot(browser: Browser, session: str, path: Path) -> None:
    data = browser.rpc('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False}, session)
    path.write_bytes(base64.b64decode(data['data']))


def run_case(binary: str, label: str, mode: str, extension: Path, css: Path, artifacts: Path) -> dict:
    browser = Browser(binary, artifacts / f'{label}-{mode}')
    try:
        version = browser.rpc('Browser.getVersion')['product']
        extension_id = browser.rpc('Extensions.loadUnpacked', {'path': str(extension)})['id']
        target = browser.rpc('Target.createTarget', {'url': 'about:blank'})['targetId']
        session = browser.rpc('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
        for method in ('Page.enable', 'Runtime.enable', 'Network.enable', 'Log.enable'):
            browser.rpc(method, session=session)
        browser.rpc('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': False}, session)
        browser.events.clear()
        browser.rpc('Page.navigate', {'url': 'chrome://newtab/'}, session)
        wait_for(browser, 'document.querySelector("#clock") && /^\\d{2}:\\d{2}$/.test(document.querySelector("#clock").textContent)', session)
        state = browser.evaluate('''JSON.parse(JSON.stringify({
            url: location.href, extensionId: chrome.runtime.id, title: document.title,
            background: getComputedStyle(document.body).backgroundColor,
            htmlBackground: getComputedStyle(document.documentElement).backgroundColor,
            bodyHeight: document.body.getBoundingClientRect().height, viewportHeight: innerHeight,
            clock: document.querySelector('#clock').textContent,
            date: document.querySelector('#date').textContent,
            lang: document.documentElement.lang,
            searchAvailable: typeof chrome.search.query === 'function',
            styles: [...document.styleSheets].map(s => s.href)
        }))''', session)
        match = re.search(r'--background:\s*(#[0-9a-fA-F]{6})', css.read_text())
        assert match, 'rendered palette lacks hex background'
        color = match.group(1)
        rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        expected = 'rgb(%d, %d, %d)' % rgb
        assert state['extensionId'] == extension_id, state
        assert state['url'].endswith('/newtab.html'), state
        assert state['background'] == state['htmlBackground'] == expected, state
        assert state['bodyHeight'] >= state['viewportHeight'], state
        assert state['lang'] == 'pt-BR' and ' de ' in state['date'], state
        assert state['searchAvailable'], state
        assert len(state['styles']) == 2 and all(s.startswith('chrome-extension://') for s in state['styles']), state
        snapshot(browser, session, artifacts / f'{label}-{mode}-desktop.png')
        browser.rpc('Emulation.setDeviceMetricsOverride', {'width': 360, 'height': 740, 'deviceScaleFactor': 1, 'mobile': True}, session)
        browser.evaluate('document.querySelector("#search").focus()', session)
        responsive = browser.evaluate('''({width: innerWidth, scroll: document.documentElement.scrollWidth,
            focus: document.activeElement.id,
            outline: getComputedStyle(document.querySelector('.search-box')).outlineStyle,
            buttonWidth: document.querySelector('button').getBoundingClientRect().width,
            buttonHeight: document.querySelector('button').getBoundingClientRect().height})''', session)
        assert responsive['scroll'] <= responsive['width'], responsive
        assert responsive['focus'] == 'search' and responsive['outline'] != 'none', responsive
        assert responsive['buttonWidth'] >= 44 and responsive['buttonHeight'] >= 44, responsive
        snapshot(browser, session, artifacts / f'{label}-{mode}-mobile.png')
        browser.evaluate('document.querySelector("#search").value = "   "; document.querySelector("#search-form").requestSubmit()', session)
        assert browser.evaluate('location.href', session) == state['url'], 'blank search navigated'
        time.sleep(.3)
        browser.rpc('Browser.getVersion')
        events = [e for e in browser.events if e.get('sessionId') == session]
        requests = [e['params']['request']['url'] for e in events if e['method'] == 'Network.requestWillBeSent']
        assert not [u for u in requests if u.startswith(('http:', 'https:', 'ws:', 'wss:'))], requests
        errors = [e for e in events if e['method'] == 'Runtime.exceptionThrown' or (
            e['method'] == 'Log.entryAdded' and e['params']['entry']['level'] == 'error')]
        assert not errors, errors
        (artifacts / f'{label}-{mode}-events.json').write_text(json.dumps(events, indent=2))
        # Intercept the actual provider navigation BEFORE a request leaves the browser.
        browser.rpc('Fetch.enable', {'patterns': [{'urlPattern': 'http*', 'requestStage': 'Request'}]}, session)
        browser.events.clear()
        query = 'hyprbar-newtab-isolated-probe'
        browser.evaluate(f'document.querySelector("#search").value = {json.dumps(query)}; document.querySelector("#search-form").requestSubmit(); true', session)
        deadline = time.monotonic() + 10
        search_url = None
        while time.monotonic() < deadline:
            browser.rpc('Browser.getVersion')
            paused = [e for e in browser.events if e['method'] == 'Fetch.requestPaused']
            if paused:
                for event in paused:
                    request = event['params']
                    url = request['request']['url']
                    if query in url:
                        search_url = url
                    browser.rpc('Fetch.failRequest', {'requestId': request['requestId'], 'errorReason': 'Aborted'}, session)
                break
            time.sleep(.1)
        assert search_url and query in parse_qs(urlparse(search_url).query).get('q', []), ('search did not reach default provider', browser.events)
        result = dict(browser=label, version=version, palette=mode, **state,
                      requests=requests, cspErrors=errors, responsive=responsive, searchUrl=search_url,
                      assertions=['chrome://newtab override', 'rendered full-page background', 'Portuguese clock/date',
                                  'local CSS only; zero remote page requests', 'zero CSP/runtime errors',
                                  '360px responsive; visible focus; 44px button', 'blank search ignored',
                                  'real default-provider search intercepted before network'])
        print(f'PASS {label} {mode}: {expected}; override, local CSS, no network/CSP errors, responsive, search', flush=True)
        return result
    finally:
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extension', type=Path, default=ROOT)
    parser.add_argument('--palette-json', type=Path, default=ROOT.parents[1] / 'assets/palettes/hyprbar moderno.json')
    parser.add_argument('--artifacts', type=Path)
    args = parser.parse_args()
    artifacts = args.artifacts or Path(tempfile.mkdtemp(prefix='hyprbar-newtab-', dir=SCRATCH))
    artifacts.mkdir(parents=True, exist_ok=True)
    print('Artifacts:', artifacts, flush=True)
    template = ROOT / 'palette.css.in'
    assert template.is_file(), 'missing Hyprbar palette template'
    rendered = {}
    render_env = os.environ.copy()
    render_home = artifacts / 'render-home'
    render_home.mkdir(exist_ok=True)
    render_env.update(HOME=str(render_home), HYPRBAR_CONFIG_HOME=str(render_home / 'config'),
                      XDG_CONFIG_HOME=str(render_home / 'config'), XDG_STATE_HOME=str(render_home / 'state'),
                      XDG_CACHE_HOME=str(render_home / 'cache'), XDG_DATA_HOME=str(render_home / 'data'))
    for mode in ('dark', 'light'):
        css = artifacts / f'{mode}-palette.css'
        command = ['hyprbar', 'theme', '--theme-json', str(args.palette_json), f'--{mode}', '--default-mode', mode, '--render', f'{template}:{css}']
        completed = subprocess.run(command, check=True, capture_output=True, text=True, env=render_env)
        (artifacts / f'{mode}-render.log').write_text(completed.stdout + completed.stderr)
        assert '{{' not in css.read_text(), 'unresolved template tokens'
        rendered[mode] = css
    assert rendered['dark'].read_text() != rendered['light'].read_text()
    palette = args.extension / 'palette.css'
    original = palette.read_bytes()
    results = []
    try:
        for label, executable in [('chrome', 'google-chrome-stable'), ('brave', 'brave-browser')]:
            binary = shutil.which(executable)
            assert binary, f'missing {executable}'
            for mode, css in rendered.items():
                palette.write_bytes(css.read_bytes())
                results.append(run_case(binary, label, mode, args.extension.resolve(), css, artifacts))
        for label in ('chrome', 'brave'):
            colors = [r['background'] for r in results if r['browser'] == label]
            assert len(set(colors)) == 2, (label, colors)
        (artifacts / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print('PASS both browsers changed computed background across two real Hyprbar renders', flush=True)
    finally:
        palette.write_bytes(original)
        assert palette.read_bytes() == original
        print('Source palette restored; all isolated test browsers reaped.', flush=True)


if __name__ == '__main__':
    main()
