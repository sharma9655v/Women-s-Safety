FROM node:22-alpine AS base
# Non-TTY-safe corepack (never prompt for the package-manager download),
# and disable Next.js telemetry everywhere.
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    NEXT_TELEMETRY_DISABLED=1
# Shared pnpm settings for ALL stages (deps + builder must resolve identical
# config, otherwise pnpm's deps-status check flags node_modules as stale).
# pnpm 11 ignores NPM_CONFIG_* env vars for these keys, hence config set.
# fetch-timeout must cover a single ~33MB tarball (@next/swc-linux-x64-musl)
# over a degraded link.
RUN corepack enable && \
    pnpm config set registry https://registry.npmjs.org/ && \
    pnpm config set fetch-retries 5 && \
    pnpm config set fetch-timeout 300000 && \
    pnpm config set store-dir /pnpm/store && \
    pnpm config set verify-deps-before-run false

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
# Persistent BuildKit cache for the pnpm store: interrupted builds resume
# instead of re-downloading all packages. Retry loop rides out transient
# registry/proxy stalls; each retry reuses everything already in the store.
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    ok=0; \
    for i in 1 2 3; do \
      if pnpm install --frozen-lockfile; then ok=1; break; fi; \
      echo ":: pnpm install attempt $i/3 failed - retrying in 5s"; \
      sleep 5; \
    done; \
    [ "$ok" = "1" ]

FROM base AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
