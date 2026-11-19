# term-lyrics
# Copyright 2025 DaarcyDev
# Modificaciones: Copyright 2026 DairoDev
#
# Licencia MIT — ver LICENSE en la raíz del proyecto.


#term_lyrics/lyrics.py
import re
import requests

LRCLIB_GET = "https://lrclib.net/api/get"
LRCLIB_SEARCH = "https://lrclib.net/api/search"
HEADERS = {"User-Agent": "term-lyrics/0.1 (https://github.com/dairodev/term-lyrics)"}

LRC_RE = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*)")


def parse_lrc(synced: str):
    """Devuelve [(segundos, texto), ...] ordenado por tiempo."""
    out = []
    for line in synced.splitlines():
        m = LRC_RE.match(line.strip())
        if not m:
            continue
        mm, ss, frac, text = m.groups()
        frac = int(frac.ljust(3, "0")) / 1000.0
        out.append((int(mm) * 60 + int(ss) + frac, text.strip()))
    out.sort(key=lambda x: x[0])
    return out


def _fetch(params):
    try:
        r = requests.get(LRCLIB_GET, params=params, headers=HEADERS, timeout=6)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    return None


def get_synced_lyrics(artist: str, title: str, album: str = "", duration: float = 0):
    """Intenta /get exacto y luego /search como respaldo. Devuelve lista o None."""
    data = _fetch({"artist_name": artist, "track_name": title,
                   "album_name": album, "duration": int(duration)})
    if not data or not data.get("syncedLyrics"):
        try:
            r = requests.get(LRCLIB_SEARCH,
                             params={"artist_name": artist, "track_name": title},
                             headers=HEADERS, timeout=6)
            results = r.json() if r.status_code == 200 else []
        except requests.RequestException:
            results = []
        with_sync = [x for x in results if x.get("syncedLyrics")]
        if with_sync:
            data = min(with_sync, key=lambda x: abs((x.get("duration") or 0) - duration))
    if data and data.get("syncedLyrics"):
        return parse_lrc(data["syncedLyrics"])
    return None




GENIUS_SEARCH = "https://genius.com/api/search/multi"


def fetch_lyrics(artist: str, title: str):
    """Respaldo: letra plana desde Genius (sin timestamps)."""
    try:
        r = requests.get(GENIUS_SEARCH,
                         params={"q": f"{artist} {title}"},
                         headers=HEADERS, timeout=6)
        if r.status_code != 200:
            return None
        sections = r.json().get("response", {}).get("sections", [])
        hits = [h for s in sections for h in s.get("hits", [])]
        song_hits = [h["result"] for h in hits if h.get("type") == "song"]
        if not song_hits:
            return None
        url = song_hits[0].get("url")
        if not url:
            return None

        page = requests.get(url, headers=HEADERS, timeout=8)
        if page.status_code != 200:
            return None

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(page.text, "html.parser")
        blocks = soup.select('[data-lyrics-container="true"]')
        if not blocks:
            return None
        text = "\n".join(b.get_text("\n", strip=True) for b in blocks)
        return text or None
    except Exception:
        return None
