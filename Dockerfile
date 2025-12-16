# Use official Python image
FROM vortex.kronshtadt.ru:8443/maas-proxy/python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build argument for Linux proxy URL
ARG LINUX_PROXY_URL

# This allows building with or without proxy depending on environment
RUN if [ -n "$LINUX_PROXY_URL" ]; then \
        echo "Configuring apt proxy: $LINUX_PROXY_URL" && \
        echo "Acquire::http::Proxy \"$LINUX_PROXY_URL\";" > /etc/apt/apt.conf.d/99proxy && \
        echo "Acquire::https::Proxy \"$LINUX_PROXY_URL\";" >> /etc/apt/apt.conf.d/99proxy; \
    else \
        echo "No proxy configured - using direct internet access"; \
    fi

# Install system dependencies
# Use Pandoc + texlive-xetex for DOCX to PDF conversion with Unicode support (lighter than LibreOffice)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    pandoc \
    texlive-xetex \
    texlive-fonts-recommended \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

COPY pip.conf /etc/pip.conf

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create uploads directory
RUN mkdir -p uploads/3d_models uploads/temp uploads/documents uploads/previews data logs

# Create non-root user for security
#RUN useradd --create-home --shell /bin/bash app && \
#    chown -R app:app /app
#USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"] 
