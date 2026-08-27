# Build stage
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
COPY . .

# Install dependencies for Next.js build (need typescript, etc.)
RUN npm install --no-audit

# Build the app - use standalone output for Docker deployment
ENV NODE_ENV=production
RUN npm run build

# Production stage - use standalone output for minimal image size
FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3070

# Copy standalone output from builder
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Update package.json for standalone mode
RUN node -e "const pkg=require('./package.json'); delete pkg.devDependencies; pkg.scripts={}; require('fs').writeFileSync('package.json', JSON.stringify(pkg,null,2))"

EXPOSE 3070

CMD ["node", "server.js"]
