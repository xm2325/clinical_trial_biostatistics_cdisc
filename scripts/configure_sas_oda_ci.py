from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path


REGION_HOSTS = {
    "euw1": ["odaws01-euw1.oda.sas.com", "odaws02-euw1.oda.sas.com"],
    "usw2": ["odaws01-usw2.oda.sas.com", "odaws02-usw2.oda.sas.com"],
    "usw2-2": ["odaws01-usw2-2.oda.sas.com", "odaws02-usw2-2.oda.sas.com"],
    "apse1": ["odaws01-apse1.oda.sas.com", "odaws02-apse1.oda.sas.com"],
    "apse1-2": ["odaws01-apse1-2.oda.sas.com", "odaws02-apse1-2.oda.sas.com"],
}


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"required environment variable {name} is empty")
    if "\n" in value or "\r" in value:
        raise RuntimeError(f"{name} contains a newline and cannot be written to .authinfo safely")
    return value


def main() -> None:
    user = _required_env("SAS_ODA_USER")
    password = _required_env("SAS_ODA_PASSWORD")
    if any(ch.isspace() for ch in user):
        raise RuntimeError("SAS_ODA_USER contains whitespace; use the exact ODA username/email")
    if any(ch.isspace() for ch in password):
        raise RuntimeError(
            "SAS_ODA_PASSWORD contains whitespace; SASPy .authinfo credentials must be token-safe"
        )

    region = (os.environ.get("SAS_ODA_REGION", "") or "euw1").strip().lower()
    if region not in REGION_HOSTS:
        allowed = ", ".join(sorted(REGION_HOSTS))
        raise RuntimeError(f"unsupported SAS_ODA_REGION={region!r}; expected one of: {allowed}")

    java = shutil.which("java")
    if not java:
        raise RuntimeError("Java executable was not found on PATH")

    runner_temp = Path(os.environ.get("RUNNER_TEMP", "/tmp")).resolve()
    runner_temp.mkdir(parents=True, exist_ok=True)
    cfgfile = runner_temp / "sascfg_personal.py"
    hosts = REGION_HOSTS[region]
    cfgfile.write_text(
        "SAS_config_names = ['oda']\n"
        "SAS_config_options = {'lock_down': True, 'verbose': False}\n"
        "oda = {\n"
        f"    'java': {java!r},\n"
        f"    'iomhost': {hosts!r},\n"
        "    'iomport': 8591,\n"
        "    'authkey': 'oda',\n"
        "    'encoding': 'utf-8',\n"
        "}\n",
        encoding="utf-8",
    )

    authinfo = Path.home() / ".authinfo"
    authinfo.write_text(f"oda user {user} password {password}\n", encoding="utf-8")
    authinfo.chmod(stat.S_IRUSR | stat.S_IWUSR)

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as handle:
            handle.write(f"cfgfile={cfgfile}\n")
            handle.write(f"region={region}\n")

    print(
        "Configured ephemeral SASPy Remote IOM connection "
        f"for ODA region {region}; credentials were written only to runner-local .authinfo."
    )


if __name__ == "__main__":
    main()
