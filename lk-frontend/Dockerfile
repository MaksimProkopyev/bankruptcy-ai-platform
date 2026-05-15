FROM node:20-alpine
RUN npm install -g pnpm
WORKDIR /app
COPY package.json pnpm-workspace.yaml ./
COPY packages/ ./packages/
COPY lk-frontend/ ./lk-frontend/
RUN pnpm install --filter lk-frontend
WORKDIR /app/lk-frontend
RUN pnpm run build
CMD ["pnpm", "start"]
