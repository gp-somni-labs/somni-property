FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - git: for GitPython
# - libmagic1: for file type detection
# - WeasyPrint dependencies: libpango, libcairo, libgdk-pixbuf, fonts
RUN apt-get update && \
    apt-get install -y \
        git \
        libmagic1 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libcairo2 \
        shared-mime-info \
        fonts-liberation && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start server with full backend (Pydantic v2 issues fixed!)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
