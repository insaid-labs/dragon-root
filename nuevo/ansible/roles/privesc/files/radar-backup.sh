#!/bin/bash
# ===========================================================================
#  radar-backup.sh  --  Dragon Radar working-directory archiver
#  Capsule Corp build/maintenance utility.
#
#  Usage:  radar-backup.sh <directory>
#
#  Runs as root via sudo for the goku account (see /etc/sudoers.d/goku) so the
#  ops team can snapshot a radar build dir without juggling permissions.
# ===========================================================================
set -u

BACKUP_SRC="$1"
BACKUP_DST="/var/backups/radar"

mkdir -p "$BACKUP_DST"

cd "$BACKUP_SRC" || { echo "[radar-backup] cannot enter '$BACKUP_SRC'"; exit 1; }

echo "[radar-backup] archiving $(pwd) ..."

# Archive everything in the target directory.
#   BUG (intended): the glob below is unquoted, so any file whose NAME looks
#   like a tar option (e.g. --checkpoint-action=...) is passed straight to tar
#   as an option. Classic GTFOBins tar wildcard injection.
/bin/tar czf "$BACKUP_DST/radar-$(date +%F-%H%M%S).tar.gz" *

echo "[radar-backup] backup written to $BACKUP_DST"
