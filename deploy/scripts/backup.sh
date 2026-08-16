#!/usr/bin/env bash
set -euo pipefail

readonly reason="${1:-scheduled}"
readonly deploy_dir="/opt/papermast"
readonly compose_file="${deploy_dir}/compose.production.yml"
readonly environment_file="${deploy_dir}/.env"
readonly backup_dir="/var/backups/papermast/mysql"
readonly timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
readonly final_file="${backup_dir}/papermast-${timestamp}-${reason}.sql.gz"
readonly temporary_file="${final_file}.partial"

install -d -m 700 "$backup_dir"

docker compose \
    --file "$compose_file" \
    --env-file "$environment_file" \
    exec --no-TTY mysql \
    sh -c 'exec mysqldump \
        --user=papermast \
        --password="$MYSQL_PASSWORD" \
        --single-transaction \
        --quick \
        --skip-lock-tables \
        papermast' \
    | gzip --stdout > "$temporary_file"

gzip --test "$temporary_file"
test -s "$temporary_file"
mv "$temporary_file" "$final_file"
chmod 600 "$final_file"

find "$backup_dir" -type f -name 'papermast-*.sql.gz' -mtime +28 -delete
echo "$final_file"
