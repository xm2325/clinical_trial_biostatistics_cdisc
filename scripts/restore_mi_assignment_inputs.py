from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    outputs = ROOT / "outputs"
    pairs = [
        (outputs / "adsl_style_actual_pre_mi.csv", outputs / "adsl_style.csv"),
        (outputs / "adqs_actot_style_actual_pre_mi.csv", outputs / "adqs_actot_style.csv"),
    ]
    restored = []
    for backup, original in pairs:
        if not backup.exists():
            print(f"MI restore skipped; backup not present: {backup}")
            continue
        expected = _sha256(backup)
        shutil.copyfile(backup, original)
        observed = _sha256(original)
        if observed != expected:
            raise RuntimeError(f"MI input restore hash mismatch for {original}: {observed} != {expected}")
        restored.append(f"{original.name}:{observed}")
    print("MI assignment input restore: " + ("; ".join(restored) if restored else "no backups present"))


if __name__ == "__main__":
    main()
