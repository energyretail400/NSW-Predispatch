"""
Downloads the latest AEMO ZIP files from NEMWEB.
"""

import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path

INPUT_FOLDER = Path(__file__).parent / "data"

# ── Medium Term PASA ──────────────────────────────────────────────────────────

NEMWEB_URL = "https://www.nemweb.com.au/REPORTS/CURRENT/Medium_Term_PASA_Reports/"
FILE_PATTERN = re.compile(r"PUBLIC_MTPASA_(\d{12})_\d+\.zip", re.IGNORECASE)


def _parse_date_from_filename(filename: str) -> str:
    m = FILE_PATTERN.search(filename)
    return m.group(1) if m else ""


def get_latest_local() -> Path | None:
    folder = INPUT_FOLDER / "MTPASA"
    folder.mkdir(parents=True, exist_ok=True)
    local = sorted(folder.glob("PUBLIC_MTPASA_*.zip"),
                   key=lambda p: _parse_date_from_filename(p.name), reverse=True)
    return local[0] if local else None


# ── Short Term PASA ───────────────────────────────────────────────────────────

STPASA_URL = "https://www.nemweb.com.au/REPORTS/CURRENT/Short_Term_PASA_Reports/"
STPASA_FILE_PATTERN = re.compile(r"PUBLIC_STPASA_(\d{12})_\d+\.zip", re.IGNORECASE)


def _parse_stpasa_date(filename: str) -> str:
    m = STPASA_FILE_PATTERN.search(filename)
    return m.group(1) if m else ""


def download_latest_stpasa() -> tuple[Path | None, str]:
    folder = INPUT_FOLDER / "STPASA"
    folder.mkdir(parents=True, exist_ok=True)

    resp = requests.get(STPASA_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    files = []
    for a in soup.find_all("a", href=True):
        name = a["href"].split("/")[-1]
        if STPASA_FILE_PATTERN.search(name):
            url = a["href"] if a["href"].startswith("http") else STPASA_URL + name
            files.append({"name": name, "url": url, "date": _parse_stpasa_date(name)})

    if not files:
        return None, "No STPASA files found on NEMWEB."

    files.sort(key=lambda x: x["date"], reverse=True)
    newest = files[0]
    local = {f.name for f in folder.glob("PUBLIC_STPASA_*.zip")}

    if newest["name"] in local:
        return folder / newest["name"], f"STPASA data is up to date ({newest['name']})"

    dest = folder / newest["name"]
    with requests.get(newest["url"], stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)

    return dest, f"Downloaded: {newest['name']}"


def get_latest_stpasa_local() -> Path | None:
    folder = INPUT_FOLDER / "STPASA"
    folder.mkdir(parents=True, exist_ok=True)
    local = sorted(folder.glob("PUBLIC_STPASA_*.zip"),
                   key=lambda p: _parse_stpasa_date(p.name), reverse=True)
    return local[0] if local else None


# ── P5 Predispatch (P5MIN) ────────────────────────────────────────────────────

P5MIN_URL = "https://www.nemweb.com.au/REPORTS/CURRENT/P5_Reports/"
P5MIN_FILE_PATTERN = re.compile(r"PUBLIC_P5MIN_(\d{12})_\d+\.zip", re.IGNORECASE)


def _parse_p5min_date(filename: str) -> str:
    m = P5MIN_FILE_PATTERN.search(filename)
    return m.group(1) if m else ""


def download_latest_p5min() -> tuple[Path | None, str]:
    folder = INPUT_FOLDER / "P5MIN"
    folder.mkdir(parents=True, exist_ok=True)

    resp = requests.get(P5MIN_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    files = []
    for a in soup.find_all("a", href=True):
        name = a["href"].split("/")[-1]
        if P5MIN_FILE_PATTERN.search(name):
            url = a["href"] if a["href"].startswith("http") else P5MIN_URL + name
            files.append({"name": name, "url": url, "date": _parse_p5min_date(name)})

    if not files:
        return None, "No P5MIN files found on NEMWEB."

    files.sort(key=lambda x: x["date"], reverse=True)
    newest = files[0]
    local = {f.name for f in folder.glob("PUBLIC_P5MIN_*.zip")}

    if newest["name"] in local:
        return folder / newest["name"], f"P5MIN data is up to date ({newest['name']})"

    dest = folder / newest["name"]
    with requests.get(newest["url"], stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)

    return dest, f"Downloaded: {newest['name']}"


def get_latest_p5min_local() -> Path | None:
    folder = INPUT_FOLDER / "P5MIN"
    folder.mkdir(parents=True, exist_ok=True)
    local = sorted(folder.glob("PUBLIC_P5MIN_*.zip"),
                   key=lambda p: _parse_p5min_date(p.name), reverse=True)
    return local[0] if local else None


# ── 30-min Predispatch ────────────────────────────────────────────────────────

PREDISPATCH_URL = "https://www.nemweb.com.au/REPORTS/CURRENT/Predispatch_Reports/"
PREDISPATCH_FILE_PATTERN = re.compile(r"PUBLIC_PREDISPATCH_(\d{12})_\d+_LEGACY\.zip", re.IGNORECASE)


def _parse_predispatch_date(filename: str) -> str:
    m = PREDISPATCH_FILE_PATTERN.search(filename)
    return m.group(1) if m else ""


def download_latest_predispatch() -> tuple[Path | None, str]:
    folder = INPUT_FOLDER / "PREDISPATCH"
    folder.mkdir(parents=True, exist_ok=True)

    resp = requests.get(PREDISPATCH_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    files = []
    for a in soup.find_all("a", href=True):
        name = a["href"].split("/")[-1]
        if PREDISPATCH_FILE_PATTERN.search(name):
            url = a["href"] if a["href"].startswith("http") else PREDISPATCH_URL + name
            files.append({"name": name, "url": url, "date": _parse_predispatch_date(name)})

    if not files:
        return None, "No Predispatch files found on NEMWEB."

    files.sort(key=lambda x: x["date"], reverse=True)
    newest = files[0]
    local = {f.name for f in folder.glob("PUBLIC_PREDISPATCH_*_LEGACY.zip")}

    if newest["name"] in local:
        return folder / newest["name"], f"Predispatch data is up to date ({newest['name']})"

    dest = folder / newest["name"]
    with requests.get(newest["url"], stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)

    return dest, f"Downloaded: {newest['name']}"


def get_latest_predispatch_local() -> Path | None:
    folder = INPUT_FOLDER / "PREDISPATCH"
    folder.mkdir(parents=True, exist_ok=True)
    local = sorted(folder.glob("PUBLIC_PREDISPATCH_*_LEGACY.zip"),
                   key=lambda p: _parse_predispatch_date(p.name), reverse=True)
    return local[0] if local else None


# ── Dispatch IS ───────────────────────────────────────────────────────────────

DISPATCHIS_URL = "https://www.nemweb.com.au/Reports/CURRENT/DispatchIS_Reports/"
DISPATCHIS_FILE_PATTERN = re.compile(r"PUBLIC_DISPATCHIS_(\d{12})_\d+\.zip", re.IGNORECASE)


def _parse_dispatchis_date(filename: str) -> str:
    m = DISPATCHIS_FILE_PATTERN.search(filename)
    return m.group(1) if m else ""


def download_latest_dispatchis() -> tuple[Path | None, str]:
    folder = INPUT_FOLDER / "DISPATCHIS"
    folder.mkdir(parents=True, exist_ok=True)

    resp = requests.get(DISPATCHIS_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    files = []
    for a in soup.find_all("a", href=True):
        name = a["href"].split("/")[-1]
        if DISPATCHIS_FILE_PATTERN.search(name):
            url = a["href"] if a["href"].startswith("http") else DISPATCHIS_URL + name
            files.append({"name": name, "url": url, "date": _parse_dispatchis_date(name)})

    if not files:
        return None, "No DispatchIS files found on NEMWEB."

    files.sort(key=lambda x: x["date"], reverse=True)
    newest = files[0]
    local = {f.name for f in folder.glob("PUBLIC_DISPATCHIS_*.zip")}

    if newest["name"] in local:
        return folder / newest["name"], f"DispatchIS up to date ({newest['name']})"

    dest = folder / newest["name"]
    with requests.get(newest["url"], stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)

    return dest, f"Downloaded: {newest['name']}"


def get_latest_dispatchis_local() -> Path | None:
    folder = INPUT_FOLDER / "DISPATCHIS"
    folder.mkdir(parents=True, exist_ok=True)
    local = sorted(folder.glob("PUBLIC_DISPATCHIS_*.zip"),
                   key=lambda p: _parse_dispatchis_date(p.name), reverse=True)
    return local[0] if local else None
