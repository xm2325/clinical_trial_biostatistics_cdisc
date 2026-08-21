from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

SOURCE_URLS = {
    "dm": "https://raw.githubusercontent.com/pharmaverse/pharmaversesdtm/main/inst/extdata/dm.csv",
    "ae": "https://raw.githubusercontent.com/pharmaverse/pharmaversesdtm/main/inst/extdata/ae.csv",
    "ds": "https://raw.githubusercontent.com/pharmaverse/pharmaversesdtm/main/inst/extdata/ds.csv",
    "ex": "https://raw.githubusercontent.com/pharmaverse/pharmaversesdtm/main/inst/extdata/ex.csv",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "clinical-biostatistics-cdisc-portfolio/0.2"})
    with urlopen(req, timeout=60) as response, destination.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def ensure_inputs(cache_dir: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for domain, url in SOURCE_URLS.items():
        path = cache_dir / f"{domain}.csv"
        if not path.exists():
            download_file(url, path)
        paths[domain] = path
    return paths


def read_sdtm(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, na_values=["NA", ""], keep_default_na=True)
