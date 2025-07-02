FROM python:3.11-slim
WORKDIR /app
#COPY *.py ./
#COPY *.yml ./

# Install shared libraries via git
ARG GITHUB_TOKEN
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir git+https://$GITHUB_TOKEN@github.com/killfile/apptracker_shared.git@main#egg=apptracker_shared
RUN pip install --no-cache-dir git+https://$GITHUB_TOKEN@github.com/killfile/apptracker_database.git@main#egg=apptracker_database

# COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
