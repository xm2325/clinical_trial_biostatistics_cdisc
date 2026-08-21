from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

PHARMAVERSE_SOURCE_URLS = {
    "dm": "https://raw.githubusercontent.com/pharmaverse/pharmaversesdtm/main/inst/extdata/dm.csv",
    "ae": "https://raw.githubusercontent.com/pharmaverse/pharmaversesdtm/main/inst/extdata/ae.csv",
    "ds": "https://raw.githubusercontent.com/pharmaverse/pharmaversesdtm/main/inst/extdata/ds.csv",
    "ex": "https://raw.githubusercontent.com/pharmaverse/pharmaversesdtm/main/inst/extdata/ex.csv",
}
SOURCE_URLS = PHARMAVERSE_SOURCE_URLS

CDISC_PILOT_COMMIT = "667511d4b183871d74392ba691c935c38d431d39"
CDISC_BASE = (
    "https://raw.githubusercontent.com/cdisc-org/sdtm-adam-pilot-project/"
    f"{CDISC_PILOT_COMMIT}/updated-pilot-submission-package/900172/m5/datasets/cdiscpilot01"
)
OFFICIAL_JSON_URLS = {
    "qs": f"{CDISC_BASE}/tabulations/sdtm/qs.json",
    "adqscibc_reference": f"{CDISC_BASE}/analysis/adam/datasets/adqscibc.json",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "clinical-biostatistics-cdisc-portfolio/0.3"})
    with urlopen(req, timeout=120) as response, destination.open("wb") as out:
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


def ensure_official_json_inputs(cache_dir: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, url in OFFICIAL_JSON_URLS.items():
        path = cache_dir / f"{name}.json"
        if not path.exists():
            download_file(url, path)
        paths[name] = path
    return paths


def read_sdtm(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, na_values=["NA", ""], keep_default_na=True)


def read_dataset_json(path: Path) -> pd.DataFrame:
    """Read a CDISC Dataset-JSON 1.x file into a DataFrame."""
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    columns = [c["name"] for c in payload["columns"]]
    rows = payload["rows"]
    if any(len(row) != len(columns) for row in rows):
        raise ValueError(f"Dataset-JSON row width does not match metadata in {path.name}")
    return pd.DataFrame.from_records(rows, columns=columns)
