FROM node:20-alpine AS builder
WORKDIR /app

# copy package files first for layer caching
COPY package*.json ./
RUN npm ci --production

COPY . .

ENV NODE_ENV=production
EXPOSE 3000

CMD ["node", "index.js"]
