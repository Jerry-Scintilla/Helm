# ── Stage 1: build Vue SPA ────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

COPY package.json ./
# 不复制 pnpm-lock.yaml：lock 文件在 Windows 生成，不含 linux-x64-musl 原生绑定。
# 在容器内做一次全新 install，让 pnpm 为当前平台（Linux musl）解析正确的 rolldown 绑定。
RUN pnpm install

COPY . .

# VITE_API_URL is intentionally left empty: nginx on the same origin handles routing
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN pnpm run build-only

# ── Stage 2: nginx static server + reverse proxy ──────────────────────────────
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
