# Một dịch vụ cho Render: giao diện (frontend/dist) + cầu AG-UI /agent bọc agent thật (codebase/agent.py).
# Agent và bridge chỉ dùng thư viện chuẩn Python, không pip install. Key model đặt ở biến môi trường của Render,
# không nằm trong image (xem .dockerignore, render.yaml).

# 1. Build giao diện. VITE_USE_API=1: gọi /agent cùng địa chỉ với trang web.
FROM node:22-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN VITE_USE_API=1 npm run build

# 2. Chạy bridge + phục vụ giao diện.
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY codebase/ codebase/
COPY data/ data/
COPY frontend/agui/ frontend/agui/
COPY --from=web /app/frontend/dist frontend/dist
RUN useradd --create-home app && mkdir -p traces && chown -R app /app
USER app
# Render đặt PORT; server.py tự nghe 0.0.0.0:$PORT khi có PORT.
CMD ["python", "frontend/agui/server.py"]
