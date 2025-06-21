# Use an official Python runtime as a parent image
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the app code (for prod, will be overridden in dev)
COPY app.py ./

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Default to production mode
ENV FLASK_ENV=production

# Allow switching to dev mode with a build arg
ARG DEV_MODE=false

# In dev mode, mount the code as a volume and enable debug
CMD ["sh", "-c", "if [ $DEV_MODE = 'true' ]; then FLASK_ENV=development flask run --host=0.0.0.0 --port=5000; else flask run --host=0.0.0.0 --port=5000; fi"]
