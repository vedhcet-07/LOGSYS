# syntax=docker/dockerfile:1
# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2: Serve with nginx ───────────────────────────────────────────────
FROM nginx:1.27-alpine

# Install envsubst (comes with gettext, already in nginx:alpine)
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/nginx.conf.template

# Default BACKEND_URL for Docker Compose (internal service name)
ENV BACKEND_URL=http://backend:8000

EXPOSE 80

# At start: substitute env vars in nginx config, then run nginx
CMD ["/bin/sh", "-c", "envsubst '${BACKEND_URL}' < /etc/nginx/conf.d/nginx.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
