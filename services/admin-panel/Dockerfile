FROM node:24-alpine AS dependencies
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY services/admin-panel/package.json ./services/admin-panel/package.json
RUN pnpm install --frozen-lockfile

FROM dependencies AS development
COPY services/admin-panel/ ./services/admin-panel/
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000
CMD ["pnpm", "--dir", "services/admin-panel", "dev"]

FROM dependencies AS build
COPY services/admin-panel/ ./services/admin-panel/
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @propadmin/admin-panel build
FROM node:24-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -S propadmin && adduser -S propadmin -G propadmin
COPY --from=build --chown=propadmin:propadmin /app/services/admin-panel/.next/standalone ./
COPY --from=build --chown=propadmin:propadmin /app/services/admin-panel/.next/static ./services/admin-panel/.next/static
USER propadmin
EXPOSE 3000
CMD ["node", "services/admin-panel/server.js"]
