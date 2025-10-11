# Development container matching Raspberry Pi environment
# Base: Debian Bookworm (matches Raspberry Pi OS Bookworm)

FROM python:3.11-bookworm

# Set working directory
WORKDIR /workspace

# Install system dependencies (matching Pi setup)
RUN apt-get update && apt-get install -y \
    git \
    i2c-tools \
    python3-smbus \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command: start interactive shell
CMD ["/bin/bash"]
