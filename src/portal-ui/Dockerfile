# ── Build stage ──────────────────────────────────────────────────────────────
FROM harbor.ai.adports.ae/node:22-alpine AS builder
WORKDIR /workspace

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npx nx build portal --configuration=production

# ── Nginx stage ───────────────────────────────────────────────────────────────
FROM harbor.ai.adports.ae/nginx:1.27-alpine AS runtime
COPY --from=builder /workspace/dist/apps/portal /usr/share/nginx/html

# SPA routing: serve index.html for all routes
RUN printf 'server {\n  listen 8080;\n  root /usr/share/nginx/html;\n  location / { try_files $uri $uri/ /index.html; }\n  add_header X-Frame-Options DENY;\n  add_header X-Content-Type-Options nosniff;\n  add_header Content-Security-Policy "default-src '"'"'self'"'"'; script-src '"'"'self'"'"'; style-src '"'"'self'"'"' '"'"'unsafe-inline'"'"';";\n}\n' > /etc/nginx/conf.d/default.conf

RUN addgroup -g 1001 appgroup && adduser -u 1001 -G appgroup -s /bin/sh -D appuser \
  && chown -R appuser:appgroup /usr/share/nginx/html /var/cache/nginx /var/run
USER 1001
EXPOSE 8080
