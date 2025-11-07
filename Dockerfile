# Stage 1: Install dependencies
FROM node:lts-alpine AS installer

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# Stage 2: Build TypeScript
FROM node:lts-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install all dependencies (including dev)
RUN npm ci

# Copy source code
COPY src ./src

# Build TypeScript
RUN npm run build

# Stage 3: Runtime
FROM node:lts-alpine AS runtime

WORKDIR /app

# Copy production dependencies from installer
COPY --from=installer /app/node_modules ./node_modules

# Copy built files from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./

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

