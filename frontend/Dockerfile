# syntax=docker/dockerfile:1

# ---------- Giai đoạn 1: build React ----------
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
RUN npm run build

# ---------- Giai đoạn 2: Nginx phục vụ file tĩnh và chuyển tiếp /api ----------
# Bản "unprivileged": chạy bằng user thường, lắng nghe cổng 8080
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
