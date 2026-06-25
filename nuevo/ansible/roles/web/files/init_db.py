#!/usr/bin/env python3
"""Seed the Dragon Radar SQLite database.

Reads credential values from the environment so the Ansible role stays the
single source of truth:
    WEB_USER, WEB_PASS   -> the dashboard login leaked over POP3
    BULMA_WEB_PASS       -> bulma's (unused-in-chain) admin login
"""
import os
import sqlite3

DB = os.environ.get("DB_PATH", "/var/capsule/capsule.db")

os.makedirs(os.path.dirname(DB), exist_ok=True)
con = sqlite3.connect(DB)
c = con.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role     TEXT NOT NULL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    token   TEXT NOT NULL,
    created TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

users = [
    (os.environ.get("WEB_USER", "goku"),  os.environ.get("WEB_PASS", "9000"),        "field-tester"),
    ("bulma", os.environ.get("BULMA_WEB_PASS", "senzu_b3an_2015"), "admin"),
]
for username, password, role in users:
    c.execute(
        "INSERT OR REPLACE INTO users (username, password, role) VALUES (?,?,?)",
        (username, password, role),
    )

con.commit()
con.close()
print(f"[init_db] seeded {DB} with {len(users)} users")
