FROM python:3.11-slim

# System deps for Playwright and PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install chromium

# Copy application code preserving directory structure
# main.py expects: /app/backend/main.py, /app/frontend/, /app/templates/
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY templates/ ./templates/

# Create tmp directories for PDFs and screenshots
RUN mkdir -p .tmp/applications .tmp/screenshots

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]