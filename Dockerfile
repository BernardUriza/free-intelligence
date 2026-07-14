# The waiter, in a box — built for Azure Container Apps.
#
# Three stages so the thing that ships carries no compiler, no dev dependency and
# no source: deps -> build -> a runtime layer holding only Next's `standalone`
# output (the server plus the node_modules it actually reached).
#
# The container stores nothing, exactly like the daemon's (aire-server, decision
# #4). It reads a database it does not own and can be destroyed at any moment
# without losing a byte.

FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# The build never reaches Postgres: every page is `force-dynamic`, so nothing is
# prerendered and no DSN is needed here. The database is a RUNTIME dependency —
# baking one in would put a credential in an image layer.
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:24-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Do not serve the internet as root.
RUN addgroup -g 1001 -S nodejs && adduser -S waiter -u 1001
USER waiter

COPY --from=build --chown=waiter:nodejs /app/.next/standalone ./
COPY --from=build --chown=waiter:nodejs /app/.next/static ./.next/static

EXPOSE 3000

# AIRE_DATABASE_URL is injected as a Container Apps secret at runtime — never here.
CMD ["node", "server.js"]
