# syntax=docker/dockerfile:1
#
# One file, two outputs: the `dev` stage docker-compose runs, and the default
# `runtime` stage a release publishes. They were going to be two files, which is
# how the pnpm pin in here already drifted from the one in .github/workflows
# (11.17.0 against 10). A single base stage means there is one version to bump.
#
# RUNTIME CONFIGURATION
#
# Every value this app reads from the environment comes through
# `$env/dynamic/public`, which adapter-node resolves per process at startup, not
# at build time. So one image serves any deployment and nothing below bakes a
# hostname in:
#
#   PUBLIC_DJANGO_API_URL  required. The Django API origin, no trailing /api.
#   ORIGIN                 required in production. See below.
#   PORT                   defaults to 3000. HOST already defaults to 0.0.0.0.
#
# ORIGIN is the one that fails quietly. adapter-node compares the Origin header
# of every form POST against it, and with no ORIGIN set a proxied request is
# answered `403 Cross-site POST form submissions are forbidden`. GETs still
# work, so the app looks healthy while all 64 form actions reject. Set it to the
# public URL users type, e.g. ORIGIN=https://crm.example.com.

FROM node:24-slim AS base
# Pinned so image builds are reproducible.
RUN corepack enable && corepack prepare pnpm@11.17.0 --activate
WORKDIR /app

# Manifests only, so this layer caches on the lockfile rather than on source.
# pnpm-workspace.yaml carries dependency security overrides.
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
RUN pnpm install --frozen-lockfile


# The compose target. Source and node_modules arrive as mounts, so this stage
# deliberately copies no source of its own.
FROM deps AS dev
EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0"]


FROM deps AS builder
COPY . .
RUN pnpm build


# Install runtime dependencies only, without lifecycle scripts.
FROM base AS prod-deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
RUN pnpm install --prod --frozen-lockfile --ignore-scripts


FROM node:24-slim AS runtime
WORKDIR /app
# Allow one 25 MiB CRM file plus multipart framing; keep the request bounded.
ENV NODE_ENV=production BODY_SIZE_LIMIT=27262976

COPY --from=prod-deps --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/build ./build
# The server reads its own name and version from here on startup.
COPY --chown=node:node package.json LICENSE ./

# Present in the node images already. The server binds 3000, so it needs no
# privileged port and no reason to be root.
USER node

EXPOSE 3000
CMD ["node", "build/index.js"]
