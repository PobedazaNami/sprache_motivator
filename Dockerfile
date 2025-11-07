# Multi-stage build for Node.js TypeScript bot

# Stage 1: Build
FROM node:lts-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install all dependencies with increased timeout
RUN npm install --fetch-timeout=600000 --fetch-retries=5

# Copy source code
COPY src ./src

# Build TypeScript
RUN npm run build

# Stage 2: Runtime
FROM node:lts-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production

# Copy package files
COPY package*.json ./

# Copy node_modules from builder (we'll use all deps for now to avoid npm install issues)
COPY --from=builder /app/node_modules ./node_modules

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Change ownership
RUN chown -R nodejs:nodejs /app

# Switch to non-root user
USER nodejs

# Expose port (not required for Telegram bot, but good practice)
EXPOSE 3000

# Start the bot
CMD ["npm", "start"]

