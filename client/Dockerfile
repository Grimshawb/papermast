FROM node:24.19-alpine AS build

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH

RUN corepack enable
WORKDIR /src

COPY client/package.json client/pnpm-lock.yaml client/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY client/ ./
RUN pnpm build

FROM caddy:2.10-alpine AS runtime

COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/dist/papermast/browser /srv

EXPOSE 80 443
