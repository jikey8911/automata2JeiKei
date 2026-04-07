"""
Encrypted secret store backed by SQLite and registry helpers.

Responsibilities:
- Persist secrets for UAEs and supervisor using SQLite.
- Encrypt values with Fernet symmetric keys derived from a master key.
- Provide CRUD with defensive logging and predictable error handling.
"""

from __future__ import annotations

import base64
import logging
import os
import sqlite3
from pathlib import Path
from typing import Iterable, Optional, List

from cryptography.fernet import Fernet, InvalidToken

# Default locations inside the AutomataEcosystem workspace
DEFAULT_DB_PATH = Path("AutomataEcosystem/data/secrets.db")
DEFAULT_KEY_PATH = Path("AutomataEcosystem/config/master.key")

# Configure module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class EncryptedSecretStore:
    """
    Minimal encrypted key-value store on SQLite + Fernet.
    Fernet key is loaded from env AUTOMATA_MASTER_KEY or a local key file.
    """

    def __init__(
        self,
        db_path: Path = DEFAULT_DB_PATH,
        key_path: Path = DEFAULT_KEY_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.key_path = Path(key_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = self._load_or_create_key()
        self._init_db()

    def _load_or_create_key(self) -> Fernet:
        env_key = os.getenv("AUTOMATA_MASTER_KEY")
        try:
            if env_key:
                logger.info("Loading Fernet key from environment variable")
                key_bytes = env_key.encode("utf-8")
                # Accept raw or base64 string
                if not self._is_base64(key_bytes):
                    key_bytes = base64.urlsafe_b64encode(key_bytes)
                return Fernet(key_bytes)

            if self.key_path.exists():
                logger.info("Loading Fernet key from %s", self.key_path)
                key_bytes = self.key_path.read_bytes().strip()
                return Fernet(key_bytes)

            logger.warning("Master key not found; generating a new one at %s", self.key_path)
            key_bytes = Fernet.generate_key()
            self.key_path.write_bytes(key_bytes)
            try:
                os.chmod(self.key_path, 0o600)
            except PermissionError:
                logger.debug("Could not chmod key file on this platform")
            return Fernet(key_bytes)
        except Exception as exc:
            logger.exception("Failed to load or create master key: %s", exc)
            raise

    @staticmethod
    def _is_base64(value: bytes) -> bool:
        try:
            return base64.urlsafe_b64encode(base64.urlsafe_b64decode(value)) == value
        except Exception:
            return False

    def _get_connection(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(
                self.db_path, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES
            )
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as exc:
            logger.exception("Unable to open SQLite database: %s", exc)
            raise

    def _init_db(self) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS secrets (
                        key TEXT PRIMARY KEY,
                        value BLOB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                conn.commit()
            logger.info("Secret store ready at %s", self.db_path)
        except Exception as exc:
            logger.exception("Failed to initialize secret database: %s", exc)
            raise

    def set_secret(self, name: str, plaintext: str) -> None:
        """
        Encrypt and store secret (insert or replace).
        """
        try:
            token = self._fernet.encrypt(plaintext.encode("utf-8"))
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO secrets (key, value) VALUES (?, ?);",
                    (name, token),
                )
                conn.commit()
            logger.info("Secret saved: %s", name)
        except Exception as exc:
            logger.exception("Failed to store secret '%s': %s", name, exc)
            raise

    def get_secret(self, name: str) -> Optional[str]:
        """
        Retrieve and decrypt a secret. Returns None if missing.
        """
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT value FROM secrets WHERE key = ?;", (name,)
                ).fetchone()
            if not row:
                logger.warning("Secret '%s' not found", name)
                return None
            try:
                return self._fernet.decrypt(row["value"]).decode("utf-8")
            except InvalidToken:
                logger.error("Invalid token when decrypting secret '%s'", name)
                raise
        except Exception as exc:
            logger.exception("Failed to retrieve secret '%s': %s", name, exc)
            raise

    def delete_secret(self, name: str) -> bool:
        """
        Delete secret by key. Returns True if a row was removed.
        """
        try:
            with self._get_connection() as conn:
                cur = conn.execute("DELETE FROM secrets WHERE key = ?;", (name,))
                conn.commit()
                removed = cur.rowcount > 0
            if removed:
                logger.info("Secret '%s' deleted", name)
            else:
                logger.warning("Secret '%s' did not exist", name)
            return removed
        except Exception as exc:
            logger.exception("Failed to delete secret '%s': %s", name, exc)
            raise

    def list_secrets(self) -> Iterable[str]:
        """
        Yield secret keys without values.
        """
        try:
            with self._get_connection() as conn:
                rows = conn.execute("SELECT key FROM secrets ORDER BY key;").fetchall()
                return [row["key"] for row in rows]
        except Exception as exc:
            logger.exception("Failed to list secrets: %s", exc)
            raise


class UaeRegistry:
    """
    Manages UAE registry rows with encrypted card data.
    """

    def __init__(self, store: EncryptedSecretStore) -> None:
        self.store = store
        self._init_table()

    def _init_table(self) -> None:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS uae_registry (
                        uae_id TEXT PRIMARY KEY,
                        bybit_subaccount_id TEXT NOT NULL,
                        sub_account_name TEXT,
                        vcc_card_id TEXT NOT NULL,
                        vcc_number_enc BLOB NOT NULL,
                        vcc_cvv_enc BLOB NOT NULL,
                        vcc_exp_enc BLOB NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                conn.commit()
        except Exception as exc:
            logger.exception("Failed to init uae_registry: %s", exc)
            raise

    def register(
        self,
        uae_id: str,
        sub_uid: str,
        card_id: str,
        card_number: str,
        card_cvv: str,
        card_exp: str,
        sub_account_name: Optional[str] = None,
        status: str = "active",
    ) -> None:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                conn.execute(
                    """
                    INSERT OR REPLACE INTO uae_registry (
                        uae_id, bybit_subaccount_id, sub_account_name, vcc_card_id,
                        vcc_number_enc, vcc_cvv_enc, vcc_exp_enc, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        uae_id,
                        sub_uid,
                        sub_account_name,
                        card_id,
                        self.store._fernet.encrypt(card_number.encode("utf-8")),
                        self.store._fernet.encrypt(card_cvv.encode("utf-8")),
                        self.store._fernet.encrypt(card_exp.encode("utf-8")),
                        status,
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.exception("Failed to register UAE %s: %s", uae_id, exc)
            raise

    def update_status(self, uae_id: str, status: str) -> None:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                conn.execute("UPDATE uae_registry SET status=? WHERE uae_id=?;", (status, uae_id))
                conn.commit()
        except Exception as exc:
            logger.exception("Failed to update status for %s: %s", uae_id, exc)
            raise

    def update_subaccount(self, uae_id: str, sub_uid: str) -> None:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                conn.execute("UPDATE uae_registry SET bybit_subaccount_id=? WHERE uae_id=?;", (sub_uid, uae_id))
                conn.commit()
        except Exception as exc:
            logger.exception("Failed to update subaccount for %s: %s", uae_id, exc)
            raise

    def list_all(self) -> Iterable[dict]:
        with self.store._get_connection() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                "SELECT uae_id, bybit_subaccount_id, vcc_card_id, vcc_number_enc, vcc_cvv_enc, vcc_exp_enc, status, created_at FROM uae_registry;"
            ).fetchall()
            return [dict(row) for row in rows]


__all__ = ["EncryptedSecretStore", "UaeRegistry", "ModelAuditLog", "DiscoveredSectors", "UaeStrategies"]


class ModelAuditLog:
    """
    Audit log for model escalations (Claude, etc.).
    """

    def __init__(self, store: EncryptedSecretStore) -> None:
        self.store = store
        self._init_table()

    def _init_table(self) -> None:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS model_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model TEXT NOT NULL,
                        reason TEXT,
                        cost_estimate REAL,
                        status TEXT NOT NULL,
                        error TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                conn.commit()
        except Exception as exc:
            logger.exception("Failed to init model_audit: %s", exc)
            raise

    def log_call(self, model: str, reason: str, cost_estimate: float, status: str, error: Optional[str] = None) -> None:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                conn.execute(
                    """
                    INSERT INTO model_audit (model, reason, cost_estimate, status, error)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (model, reason, cost_estimate, status, error),
                )
                conn.commit()
        except Exception as exc:
            logger.exception("Failed to log model audit: %s", exc)


class DiscoveredSectors:
    """
    Tracks discovered sectors and their status.
    """

    def __init__(self, store: EncryptedSecretStore) -> None:
        self.store = store
        self._init_table()

    def _init_table(self) -> None:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS discovered_sectors (
                        sector_name TEXT PRIMARY KEY,
                        discoverer_uae_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                conn.commit()
        except Exception as exc:
            logger.exception("Failed to init discovered_sectors: %s", exc)
            raise

    def upsert(self, sector_name: str, uae_id: str, status: str) -> None:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                conn.execute(
                    """
                    INSERT INTO discovered_sectors (sector_name, discoverer_uae_id, status)
                    VALUES (?, ?, ?)
                    ON CONFLICT(sector_name) DO UPDATE SET status=excluded.status, discoverer_uae_id=excluded.discoverer_uae_id;
                    """,
                    (sector_name, uae_id, status),
                )
                conn.commit()
        except Exception as exc:
            logger.exception("Failed to upsert discovered sector %s: %s", sector_name, exc)

    def list_all(self) -> Iterable[dict]:
        with self.store._get_connection() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                "SELECT sector_name, discoverer_uae_id, status, created_at FROM discovered_sectors;"
            ).fetchall()
            return [dict(row) for row in rows]


class UaeStrategies:
    """
    Stores successful investment strategies for collective intelligence.
    """

    def __init__(self, store: EncryptedSecretStore) -> None:
        self.store = store
        self._init_table()

    def _init_table(self) -> None:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS uae_strategies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        uae_id TEXT NOT NULL,
                        sector_name TEXT NOT NULL,
                        investment_idea TEXT NOT NULL,
                        code_snippet TEXT NOT NULL,
                        status TEXT NOT NULL, -- PROFITABLE, LOSS, FAILURE
                        profit_loss REAL DEFAULT 0.0,
                        execution_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                conn.commit()
        except Exception as exc:
            logger.exception("Failed to init uae_strategies: %s", exc)
            raise

    def record(self, uae_id: str, sector: str, idea: str, code: str, status: str, profit: float) -> None:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                conn.execute(
                    """
                    INSERT INTO uae_strategies (uae_id, sector_name, investment_idea, code_snippet, status, profit_loss, execution_count)
                    VALUES (?, ?, ?, ?, ?, ?, 1);
                    """,
                    (uae_id, sector, idea, code, status, profit),
                )
                conn.commit()
        except Exception as exc:
            logger.exception("Failed to record strategy: %s", exc)

    def get_profitable_strategies(self, limit: int = 10) -> List[dict]:
        try:
            with self.store._get_connection() as conn:  # type: ignore[attr-defined]
                rows = conn.execute(
                    "SELECT * FROM uae_strategies WHERE status = 'PROFITABLE' ORDER BY profit_loss DESC LIMIT ?;",
                    (limit,)
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as exc:
            logger.exception("Failed to fetch strategies: %s", exc)
            return []
