"""Shared MySQL connection and halt-time SQL for the project's scripts.

Connection settings come from MYSQL_HOST, MYSQL_PORT, MYSQL_USER,
MYSQL_PASSWORD and MYSQL_DATABASE.
"""
import os

import pymysql

# No real halt falls between 8 and 17 hours, so anything from 12 hours up
# is a data error (e.g. departure 11:02 after arrival 11:03), not a stop.
MAX_HALT_SECONDS = 43200


def connect(**kwargs):
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", "indian_railways"),
        **kwargs,
    )


def halt_seconds(alias=""):
    """Halt in seconds, corrected for stops that cross midnight (MySQL TIME
    has no date, so 23:58 -> 00:04 would otherwise read as negative)."""
    prefix = f"{alias}." if alias else ""
    return f"MOD(TIMESTAMPDIFF(SECOND, {prefix}arrival, {prefix}departure) + 86400, 86400)"


def valid_halt(alias=""):
    """Rows with both times present and a believable halt."""
    prefix = f"{alias}." if alias else ""
    return (
        f"{prefix}arrival IS NOT NULL AND {prefix}departure IS NOT NULL "
        f"AND {halt_seconds(alias)} < {MAX_HALT_SECONDS}"
    )
