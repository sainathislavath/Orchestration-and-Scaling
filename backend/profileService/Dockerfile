FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci --production

COPY . .

ENV NODE_ENV=production
EXPOSE 3001

CMD ["node", "index.js"]
