from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import saspy

EXPECTED = {
    "sas.rutil.jar": "3eb56a7a9dc5caf8c3e3b90710756a63386180068b95ee3a81cac98c6382626b",
    "sas.rutil.nls.jar": "9a6e7e80477f105509627d97c0fc55f042ad8391a4f4d04759610db87599c498",
    "sastpj.rutil.jar": "057d75220b2ce0f5a072953b4d7ccf70a6556825e0b15ce579b96100549ba975",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: install_sas_oda_encryption_jars.py <SAS-ODA-JarFiles.zip>")

    archive = Path(sys.argv[1]).resolve()
    if not archive.is_file():
        raise SystemExit(f"missing encrypted-JAR archive after decryption: {archive}")

    saspy_dir = Path(saspy.__file__).resolve().parent
    iomclient = saspy_dir / "java" / "iomclient"
    if not iomclient.is_dir():
        raise SystemExit(f"SASPy iomclient directory not found: {iomclient}")

    with zipfile.ZipFile(archive) as zf:
        members = {name for name in zf.namelist() if not name.endswith("/")}
        expected_names = set(EXPECTED)
        if members != expected_names:
            raise SystemExit(
                "SAS ODA JAR bundle has unexpected contents: "
                f"expected={sorted(expected_names)} actual={sorted(members)}"
            )

        with tempfile.TemporaryDirectory(prefix="sas-oda-jars-") as tmp:
            tmpdir = Path(tmp)
            for name, expected_hash in EXPECTED.items():
                target = tmpdir / name
                with zf.open(name) as source, target.open("wb") as sink:
                    shutil.copyfileobj(source, sink)
                actual_hash = sha256(target)
                if actual_hash != expected_hash:
                    raise SystemExit(
                        f"SHA256 mismatch for {name}: expected={expected_hash} actual={actual_hash}"
                    )
                shutil.copy2(target, iomclient / name)

    installed = [name for name in EXPECTED if (iomclient / name).is_file()]
    if set(installed) != set(EXPECTED):
        raise SystemExit("not all SAS ODA encryption JARs were installed")

    print(
        "Installed and SHA256-verified SAS ODA encryption JARs into the ephemeral "
        f"SASPy runtime: {', '.join(sorted(installed))}"
    )


if __name__ == "__main__":
    main()
