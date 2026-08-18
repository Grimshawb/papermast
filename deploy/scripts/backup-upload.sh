#!/usr/bin/env bash
set -euo pipefail

readonly backup_dir="/var/backups/papermast/mysql"
readonly rclone_config="/etc/rclone/papermast.conf"
readonly remote="papermast-backups:"
readonly remote_retention_days=90

test -d "$backup_dir"
test -r "$rclone_config"

# Copy is intentionally used instead of sync: a local deletion must not
# immediately erase the off-server recovery copy. Backup filenames are unique
# and immutable, so an existing remote object should never be overwritten.
rclone copy "$backup_dir" "$remote" \
    --config "$rclone_config" \
    --include 'papermast-*.sql.gz' \
    --immutable \
    --transfers 2 \
    --checkers 4 \
    --retries 3 \
    --low-level-retries 10

# Confirm every currently retained local backup exists remotely with the same
# decrypted size before applying the longer off-server retention window.
rclone check "$backup_dir" "$remote" \
    --config "$rclone_config" \
    --include 'papermast-*.sql.gz' \
    --one-way \
    --size-only

rclone delete "$remote" \
    --config "$rclone_config" \
    --include 'papermast-*.sql.gz' \
    --min-age "${remote_retention_days}d" \
    --retries 3 \
    --low-level-retries 10

echo "Encrypted PaperMast backups are current in OneDrive."
