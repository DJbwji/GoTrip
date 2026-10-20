"""Download public demonstration photos once; site then works offline."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen, Request
ROOT = Path(__file__).resolve().parent.parent / 'static' / 'img'
ASSETS = {
    'hero.jpg': ('photo-1612554376099-fe4c6c74c3de', 1920),
    'italy.jpg': ('photo-1516483638261-f4dbaf036963', 800),
    'france.jpg': ('photo-1502602898657-3e91760cbb34', 800),
    'georgia.jpg': ('photo-1727427117223-2a91f20c419c', 800),
    'turkey.jpg': ('photo-1647955950690-989aaa0475e0', 800),
    'japan.jpg': ('photo-1493976040374-85c8e12f0c0e', 800),
    'community.jpg': ('photo-1529156069898-49953e39b3ac', 1500),
}
def download(item):
    name, (photo, width) = item
    target = ROOT / name
    if target.exists(): return name + ': exists'
    url = f'https://images.unsplash.com/{photo}?auto=format&fit=crop&w={width}&q=85'
    try:
        data = urlopen(Request(url, headers={'User-Agent':'GoTrip-Diploma/1.0'}), timeout=90).read()
        target.write_bytes(data)
        return f'{name}: {len(data)} bytes'
    except Exception as exc:
        return f'{name}: ERROR {exc}'
if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    for result in ThreadPoolExecutor(max_workers=7).map(download, ASSETS.items()): print(result)
