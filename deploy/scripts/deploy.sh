#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! $1 =~ ^[0-9a-f]{40}$ ]]; then
    echo "Usage: deploy.sh <40-character-git-sha>" >&2
    exit 2
fi

readonly release_sha="$1"
readonly deploy_dir="/opt/papermast"
readonly compose_file="${deploy_dir}/compose.yml"
readonly environment_file="${deploy_dir}/.env"
readonly release_file="${deploy_dir}/release.env"
readonly previous_release_file="${deploy_dir}/release.previous.env"
readonly next_release_file="${deploy_dir}/release.next.env"

cd "$deploy_dir"

printf '%s\n' \
    "PAPERMAST_WEB_IMAGE=ghcr.io/grimshawb/papermast-web:${release_sha}" \
    "PAPERMAST_API_IMAGE=ghcr.io/grimshawb/papermast-api:${release_sha}" \
    > "$next_release_file"

chmod 600 "$next_release_file"

if [[ -f "$release_file" ]]; then
    cp "$release_file" "$previous_release_file"
fi

docker compose \
    --file "$compose_file" \
    --env-file "$environment_file" \
    --env-file "$next_release_file" \
    pull web api

if docker compose --file "$compose_file" --env-file "$environment_file" ps --status running mysql --quiet | grep -q .; then
    /usr/local/sbin/papermast-backup pre-deploy
fi

docker compose \
    --file "$compose_file" \
    --env-file "$environment_file" \
    --env-file "$next_release_file" \
    --profile migration \
    run --rm migrate

mv "$next_release_file" "$release_file"

docker compose \
    --file "$compose_file" \
    --env-file "$environment_file" \
    --env-file "$release_file" \
    up --detach --no-build --remove-orphans

site_address="$(sed -n 's/^SITE_ADDRESS=//p' "$environment_file" | tail -n 1)"

if [[ ! $site_address =~ ^[A-Za-z0-9.-]+$ ]]; then
    echo "SITE_ADDRESS must contain only a production hostname." >&2
    exit 1
fi

for attempt in {1..30}; do
    if curl --fail --silent --show-error "https://${site_address}/health/ready" >/dev/null; then
        printf '%s\n' "$release_sha" > "${deploy_dir}/deployed-sha"
        docker image prune --force --filter "until=168h" >/dev/null
        echo "PaperMast ${release_sha} is healthy."
        exit 0
    fi

    sleep 2
done

echo "The new release failed its readiness check." >&2

if [[ -f "$previous_release_file" ]]; then
    cp "$previous_release_file" "$release_file"
    docker compose \
        --file "$compose_file" \
        --env-file "$environment_file" \
        --env-file "$release_file" \
        up --detach --no-build --remove-orphans
    echo "The previous application images were restored." >&2
fi

exit 1
