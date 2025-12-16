# Use Python 3.13 slim base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install git and clean up apt cache
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Bundle noVNC app assets locally for offline usage
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates tar && \
    rm -rf /var/lib/apt/lists/* && \
    curl -L -o /tmp/novnc.tar.gz https://github.com/novnc/noVNC/archive/refs/tags/v1.5.0.tar.gz && \
    mkdir -p /tmp/novnc && tar -xzf /tmp/novnc.tar.gz -C /tmp/novnc --strip-components=1 && \
    mkdir -p /app/app/static/novnc && \
    cp -r /tmp/novnc/app /app/app/static/novnc/app && \
    cp -r /tmp/novnc/core /app/app/static/novnc/core && \
    rm -rf /tmp/novnc /tmp/novnc.tar.gz

# Copy the rest of the application
COPY . .

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Expose port 5000
EXPOSE 5000

# Run the application with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
