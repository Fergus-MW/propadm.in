FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production HOST=0.0.0.0 PORT=8080 SIGNUPS_PATH=/tmp/signups.csv
COPY --chown=node:node landing/server.mjs landing/signup-store.mjs ./
COPY --chown=node:node landing/public/ ./public/
USER node
EXPOSE 8080
CMD ["node", "server.mjs"]
