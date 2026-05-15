FROM node:20-alpine
RUN npm install -g pnpm
WORKDIR /app
COPY package.json pnpm-workspace.yaml ./
COPY packages/ ./packages/
COPY crm-frontend/ ./crm-frontend/
RUN pnpm install --filter crm-frontend
WORKDIR /app/crm-frontend
RUN pnpm run build
CMD ["pnpm", "start"]
