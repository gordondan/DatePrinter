FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for Pillow and utilities
RUN apt-get update && apt-get install -y \
    curl \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install flask pillow

# Copy application files
COPY server.py date-printer.py ./
COPY config.py ./

# Expose port
EXPOSE 5000

# Run the server
CMD ["python", "server.py"]