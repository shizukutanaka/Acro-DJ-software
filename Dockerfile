# Acro DJ Mixer - Production Docker Image
# Multistage build for optimized final image

# Stage 1: Build
FROM python:3.11-slim as builder

WORKDIR /build

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libasound2-dev \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source
COPY . .

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e .

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2 \
    libsndfile1 \
    pulseaudio \
    dbus \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    ACRO_LOG_LEVEL=INFO

# Create non-root user
RUN useradd -m -u 1000 acro && \
    mkdir -p /app/config /app/logs && \
    chown -R acro:acro /app

USER acro

# Volume for configuration and music library
VOLUME ["/app/config", "/app/music"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from acro import __version__; print(__version__)" || exit 1

# Default command
CMD ["acro-gui"]

# Labels
LABEL maintainer="Acro Development Team" \
      description="Professional open-source DJ mixer" \
      version="2.5.0" \
      org.opencontainers.image.source="https://github.com/acro-dj/acro-dj-mixer"
