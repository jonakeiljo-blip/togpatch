#!/usr/bin/env python3
"""
One-shot TOG patch detector for GitHub Actions (no PC needed).
Polls cdn_config; on a new bundle folder it grabs the manifest, posts a Discord
alert, and records the folder in state/last_folder.txt. Stdlib only.
"""
import urllib.request, urllib.error, json, os, io, zipfile, re

INFO_URL = 'https://gs-tog-info.netmarble.com/cdn_config'
PLATFORM = 'aos'
APP_VERS = ['3.11.00','3.11.01','3.11.02',
            '3.12.00','3.12.01','3.12.02',
            '3.13.00','3.13.01','3.13.02',
            '3.14.00','3.15.00','3.16.00','3.17.00','3.18.00','3.19.00','3.20.00']
CUR_VER  = '3.12.01'
UA_UNITY = 'UnityPlayer/2022.3.62f3 (UnityWebRequest/1.0, libcurl/8.10.1-DEV)'
UA_DALVIK= 'Dalvik/2.1.0 (Linux; U; Android 9; SM-N960N Build/PQ3A.190605.003)'
STATE    = 'state/last_folder.txt'
WEBHOOK  = os.environ.get('DISCORD_WEBHOOK', '')


def get_config_one(version):
    h = {'Host': 'gs-tog-info.netmarble.com', 'User-Agent': UA_UNITY,
         'Accept-Encoding': 'identity', 'Content-Type': 'application/json',
         'Accept': 'application/json', 'version': version, 'platform': PLATFORM,
         'X-Unity-Version': '2022.3.62f3'}
    req = urllib.request.Request(INFO_URL, data=b'', headers=h, method='POST')
    with urllib.request.urlopen(req, timeout=20) as r:
        cfg = json.loads(r.read()).get('config', {})
    bi = cfg.get('bundle_info', {})
    return bi.get('folder'), bi.get('root_url'), bi.get('min_version'), cfg.get('version_info', {}).get('min')


def folder_num(f):
    try:
        return int(str(f).split('-')[0])
    except Exception:
        return -1


def ver_tuple(s):
    try:
        return tuple(int(x) for x in str(s).split('.'))
    except Exception:
        return (0,)


def get_newest():
    best = None; cur_min = None
    for v in APP_VERS:
        try:
            folder, root, minv, appmin = get_config_one(v)
        except Exception:
            continue
        if v == CUR_VER:
            cur_min = appmin
        if folder:
            n = folder_num(folder)
            if best is None or n > best[0]:
                best = (n, folder, root, minv, v)
    return best, cur_min


def fetch(url, timeout=120):
    req = urllib.request.Request(url, headers={'User-Agent': UA_DALVIK, 'Accept-Encoding': 'identity'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def discord(msg):
    if not WEBHOOK:
        print('[no webhook set] would post:\n', msg)
        return
    data = json.dumps({'content': msg}).encode()
    req = urllib.request.Request(WEBHOOK, data=data, headers={
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (TOG-Patch-Monitor)'})
    try:
        urllib.request.urlopen(req, timeout=20)
        print('discord alert sent')
    except Exception as e:
        print('discord error:', e)


def main():
    last = open(STATE).read().strip() if os.path.exists(STATE) else None
    best, cur_min = get_newest()
    if not best:
        print('no config from any probed version'); return
    num, folder, root, minv, ver = best
    print(f'newest folder = {folder} (via {ver}); last known = {last}')

    if cur_min and ver_tuple(cur_min) > ver_tuple(CUR_VER):
        discord(f"\u26a0\ufe0f **TOG**: server now requires app version **>= {cur_min}** "
                f"(forced update rolling out). A content folder may follow soon.")

    if last is None:
        os.makedirs('state', exist_ok=True); open(STATE, 'w').write(folder)
        print('baseline set ->', folder); return

    if folder != last and num >= folder_num(last):
        os.makedirs('manifests', exist_ok=True)
        count = '?'
        try:
            blob = fetch(f'{root}/{folder}/bundles.zip')
            with open(f'manifests/bundles_{folder}.zip', 'wb') as f:
                f.write(blob)
            zf = zipfile.ZipFile(io.BytesIO(blob))
            inner = zf.read(zf.namelist()[0])
            count = len(set(re.findall(rb'[0-9a-f]{32}\.ab', inner)))
        except Exception as e:
            count = f'? (manifest fetch failed: {e})'
        discord(
            f"\U0001f6a8 **NEW TOG PATCH DETECTED**\n"
            f"Folder: `{folder}`  (via version {ver})\n"
            f"min_version: `{minv}`  |  bundles in manifest: **{count}**\n"
            f"CDN: {root}/{folder}/\n"
            f"Manifest saved as a workflow artifact - full-dump from your PC when ready."
        )
        open(STATE, 'w').write(folder)
        print('NEW PATCH alerted ->', folder)
    else:
        print('no change')


if __name__ == '__main__':
    main()
