# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Bun (JavaScript runtime required by Reflex)
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Initialize Reflex with a blank template (non-interactive)
RUN echo "1" | reflex init

# Copy application code
COPY . .

# Expose frontend and backend ports
EXPOSE 3000 8001

# Run the app
CMD ["reflex", "run", "--frontend-port", "3000", "--backend-port", "8001"]