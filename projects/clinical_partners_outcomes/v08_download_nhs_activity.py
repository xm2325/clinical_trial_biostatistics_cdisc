from __future__ import annotations

import argparse
import json
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

PUBLICATIONS = {
    "2026-01": "https://digital.nhs.uk/data-and-information/publications/statistical/nhs-talking-therapies-monthly-statistics-including-employment-advisors/performance-january-2026",
    "2026-02": "https://digital.nhs.uk/data-and-information/publications/statistical/nhs-talking-therapies-monthly-statistics-including-employment-advisors/performance-february-2026",
    "2026-03": "https://digital.nhs.uk/data-and-information/publications/statistical/nhs-talking-therapies-monthly-statistics-including-employment-advisors/performance-march-2026-and-quarter-4-2025-26-data",
    "2026-04": "https://digital.nhs.uk/data-and-information/publications/statistical/nhs-talking-therapies-monthly-statistics-including-employment-advisors/performance-april-2026",
    "2026-05": "https://digital.nhs.uk/data-and-information/publications/statistical/nhs-talking-therapies-monthly-statistics-including-employment-advisors/performance-may-2026",
    "2026-06": "https://digital.nhs.uk/data-and-information/publications/statistical/nhs-talking-therapies-monthly-statistics-including-employment-advisors/performance-june-2026-and-quarter-1-2026-27-data",
}

USER_AGENT = "clinical-partners-public-data-audit/0.8 (+github.com/xm2325/clinical_trial_biostatistics_cdisc)"


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current_href: str | None = None
        self.current_text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.current_href = href
            self.current_text = []

    def handle_data(self, data: str) -> None:
        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.current_href is not None:
            text = " ".join(" ".join(self.current_text).split())
            self.links.append((self.current_href, text))
            self.current_href = None
            self.current_text = []


def collect_links(html: str) -> list[tuple[str, str]]:
    parser = LinkCollector()
    parser.feed(html)
    return parser.links


def resolve_monthly_activity_csv(publication_url: str) -> str:
    request = Request(publication_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        html = response.read().decode("utf-8", errors="replace")
    candidates: list[str] = []
    for href, text in collect_links(html):
        label = text.lower()
        if "monthly activity data file" in label and "employment advisor" not in label:
            candidates.append(urljoin(publication_url, href))
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one NHS Talking Therapies monthly activity CSV at {publication_url}; "
            f"found {len(candidates)} candidates: {candidates}"
        )
    return candidates[0]


def download_file(url: str, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=180) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    size = destination.stat().st_size
    if size < 1_000_000:
        raise RuntimeError(f"Downloaded file is unexpectedly small ({size} bytes): {url}")
    return size


def main(outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for month, publication_url in PUBLICATIONS.items():
        csv_url = resolve_monthly_activity_csv(publication_url)
        destination = outdir / f"monthly_activity_{month}.csv"
        size = download_file(csv_url, destination)
        manifest.append(
            {
                "month": month,
                "publication_url": publication_url,
                "csv_url": csv_url,
                "path": str(destination),
                "bytes": size,
            }
        )
        print(f"{month}: {size:,} bytes <- {csv_url}")
    (outdir / "v08_nhs_activity_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.out)
