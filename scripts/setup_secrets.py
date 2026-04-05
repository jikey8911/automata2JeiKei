#!/usr/bin/env python
"""
Interactive script to store Binance and Wompi credentials securely.

Usage:
    python scripts/setup_secrets.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

# Ensure repository root on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from AutomataEcosystem.core.database import EncryptedSecretStore  # noqa: E402


def prompt_secret(label: str, confirm: bool = True) -> str:
    while True:
        value = getpass.getpass(f"{label}: ").strip()
        if not confirm:
            return value
        again = getpass.getpass(f"Confirm {label}: ").strip()
        if value == again:
            return value
        print("Values did not match. Please retry.\n")


def main() -> None:
    print("AutomataEcosystem secure setup (Bybit)\n---")
    store = EncryptedSecretStore()

    bybit_key = prompt_secret("Bybit API_KEY")
    bybit_secret = prompt_secret("Bybit API_SECRET")
    bybit_master_uid = prompt_secret("Bybit MASTER_UID (cuenta Génesis)")

    store.set_secret("BYBIT_API_KEY", bybit_key)
    store.set_secret("BYBIT_API_SECRET", bybit_secret)
    store.set_secret("BYBIT_MASTER_UID", bybit_master_uid)

    print("\nSecrets stored successfully in encrypted SQLite vault.")


if __name__ == "__main__":
    main()
