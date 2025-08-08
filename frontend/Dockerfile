# Multi-stage Dockerfile for Qenergyz Frontend
# Stage 1: Build the React application
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Add metadata
LABEL maintainer="Qenergyz Team <dev@qenergyz.com>"
LABEL description="Qenergyz Energy Trading Frontend"
LABEL version="1.0.0"

# Install build dependencies for native modules
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    git

# Copy package files
COPY package*.json ./

# Install dependencies with clean cache
RUN npm ci --only=production --prefer-offline --no-audit --progress=false && \
    npm cache clean --force

# Copy source code
COPY . .

# Set build-time environment variables
ARG VITE_API_URL=http://localhost:8000
ARG VITE_REGION=middle_east
ARG VITE_DEFAULT_LANGUAGE=en
ARG BUILD_TIME
ARG VERSION

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_REGION=$VITE_REGION
ENV VITE_DEFAULT_LANGUAGE=$VITE_DEFAULT_LANGUAGE
ENV VITE_BUILD_TIME=$BUILD_TIME
ENV VITE_VERSION=$VERSION

# Build the application
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:1.25-alpine AS production

# Install additional packages for enhanced security and monitoring
RUN apk add --no-cache \
    curl \
    jq \
    tzdata

# Create non-root user
RUN addgroup -S qenergyz && adduser -S qenergyz -G qenergyz

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/nginx.conf /etc/nginx/nginx.conf

# Copy additional nginx configs
COPY docker/security-headers.conf /etc/nginx/conf.d/security-headers.conf
COPY docker/gzip.conf /etc/nginx/conf.d/gzip.conf

# Set permissions
RUN chown -R qenergyz:qenergyz /usr/share/nginx/html && \
    chown -R qenergyz:qenergyz /var/cache/nginx && \
    chown -R qenergyz:qenergyz /var/log/nginx && \
    chown -R qenergyz:qenergyz /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R qenergyz:qenergyz /var/run/nginx.pid

# Create health check script
RUN echo '#!/bin/sh\ncurl -f http://localhost:3000/health || exit 1' > /usr/local/bin/health-check.sh && \
    chmod +x /usr/local/bin/health-check.sh

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /usr/local/bin/health-check.sh

# Switch to non-root user
USER qenergyz

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# Development stage for local development with hot reload
FROM node:20-alpine AS development

WORKDIR /app

# Install development dependencies
RUN apk add --no-cache git

# Copy package files
COPY package*.json ./

# Install all dependencies including dev dependencies
RUN npm ci

# Copy source code
COPY . .

# Expose development port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]