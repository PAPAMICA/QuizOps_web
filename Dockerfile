# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# System dependencies installation
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry installation
RUN pip install poetry

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Install project
RUN poetry install --no-interaction --no-ansi

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8080

# Run the application
CMD ["/entrypoint.sh"]