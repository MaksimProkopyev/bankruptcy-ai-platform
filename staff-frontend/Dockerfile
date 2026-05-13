FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN NODE_ENV=production npm run build
EXPOSE 3001
ENV NODE_ENV=production
CMD ["npm", "start"]
