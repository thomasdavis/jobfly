FROM node:22-bookworm-slim AS web
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY backend ./backend
COPY --from=web /app/dist ./dist
ENV FLY_DATA=/brain JOBFLY_STATE=/state JOBFLY_BIND=0.0.0.0 NUMBA_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 FORWARDED_ALLOW_IPS=*
EXPOSE 8787
CMD ["python", "-m", "backend.server"]
