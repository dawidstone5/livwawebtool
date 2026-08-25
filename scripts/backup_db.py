#!/usr/bin/env python3
"""
Daily SQLite backup with rotation. Uses sqlite3's online backup API rather than
a raw file copy, since that's safe to run against a live database (won't
capture a torn/inconsistent snapshot mid-write).
"""
import gzip
import shutil
import sqlite3
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "db.sqlite3"
BACKUP_DIR = PROJECT_DIR / "backups"
RETENTION_DAYS = 14


def main():
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"db_{timestamp}.sqlite3"
    gz_path = backup_path.with_suffix(backup_path.suffix + ".gz")

    source = sqlite3.connect(str(DB_PATH))
    dest = sqlite3.connect(str(backup_path))
    with dest:
        source.backup(dest)
    source.close()
    dest.close()

    with open(backup_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    backup_path.unlink()

    cutoff = time.time() - (RETENTION_DAYS * 86400)
    for old in BACKUP_DIR.glob("db_*.sqlite3.gz"):
        if old.stat().st_mtime < cutoff:
            old.unlink()

    print(f"backup complete: {gz_path.name}")


if __name__ == "__main__":
    main()
