# Multi-stage build for Flutter web application

# Stage 1: Build the Flutter web app
FROM ghcr.io/cirruslabs/flutter:3.24.5 AS builder

WORKDIR /app

# Copy dependency files first for caching
COPY pubspec.yaml pubspec.lock* ./

# Get dependencies
RUN flutter pub get

# Copy source code
COPY . .

# Build for web with release optimizations
RUN flutter build web --release --web-renderer canvaskit

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy the built web app
COPY --from=builder /app/build/web /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
