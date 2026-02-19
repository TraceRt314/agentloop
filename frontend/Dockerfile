FROM node:20-slim AS builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .

ENV NEXT_PUBLIC_API_URL=http://localhost:8000
RUN npm run build

FROM node:20-slim
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

ENV PORT=3002
EXPOSE 3002

CMD ["node", "server.js"]
