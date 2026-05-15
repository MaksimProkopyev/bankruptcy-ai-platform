FROM node:20-alpine
RUN npm install -g pnpm
WORKDIR /app
COPY package.json pnpm-workspace.yaml ./
COPY packages/ ./packages/
COPY leadgen-frontend/ ./leadgen-frontend/
RUN pnpm install --filter leadgen-frontend
WORKDIR /app/leadgen-frontend
RUN pnpm run build
CMD ["pnpm", "start"]
