#!/usr/bin/env python3
"""Benign Dragon Radar upload processor.

Invoked every 60s by a systemd timer (radar-process.timer) and runs as
www-data. It simply moves freshly uploaded files from the uploads/ spool into
uploads/processed/ and appends a log line.

NOTE: This is intentionally NOT a privilege-escalation vector. It runs as the
same www-data account the web app already runs as, touches only www-data-owned
paths, and takes no untrusted arguments. It exists for realism and to explain
how an uploaded file ends up in uploads/processed/.
"""
import glob
import os
import shutil
import time

UPLOADS = "/var/capsule/uploads"
PROCESSED = os.path.join(UPLOADS, "processed")
LOG = "/var/capsule/tmp/.radarcache/radar-process.log"


def main() -> None:
    os.makedirs(PROCESSED, exist_ok=True)
    moved = 0
    for path in glob.glob(os.path.join(UPLOADS, "*")):
        if os.path.isdir(path):
            continue
        dest = os.path.join(PROCESSED, os.path.basename(path))
        try:
            shutil.move(path, dest)
            moved += 1
        except OSError:
            continue
    try:
        with open(LOG, "a") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} processed {moved} file(s)\n")
    except OSError:
        pass


if __name__ == "__main__":
    main()
