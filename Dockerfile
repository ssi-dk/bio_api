# Use Miniforge base image with Conda
# syntax=docker/dockerfile:1
FROM condaforge/miniforge3

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MONGO_CONNECTION='mongodb://mongo:27017/bifrost_test'

# Set working directory for the application
WORKDIR /app

# Copy the entire application (including your Python files) into the Docker image
COPY . /app/

# Install system dependencies (git, make, build tools)
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Clone cgmlst-dists repository from GitHub
RUN git clone https://github.com/tseemann/cgmlst-dists.git

# Navigate into the cloned repository and build using make
WORKDIR /app/cgmlst-dists
RUN make    

# Go back to the main application directory
WORKDIR /app

# Install Python dependencies via mamba or conda
# Install general Python dependencies first
RUN mamba install --file /app/requirements_general.txt

# Install bioinformatics-related dependencies from Bioconda
RUN mamba install -c bioconda --file /app/requirements_bioconda.txt

# Create a volume for external data (optional)
VOLUME /dmx_data

# Expose the necessary port (e.g., for a FastAPI or Uvicorn app)
EXPOSE 8000

# Set the entry point to start the app with Uvicorn (if using FastAPI, for example)
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
