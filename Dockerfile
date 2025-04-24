# syntax=docker/dockerfile:1
FROM condaforge/miniforge3

# Set up environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MONGO_CONNECTION='mongodb://mongo:27017/bifrost_test'

# Create working directory
WORKDIR /app

# Install system dependencies and gosu
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gosu \
        git \
        adduser \
        libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Add non-root user
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup appuser

# Install Python dependencies
COPY requirements_general.txt requirements_bioconda.txt /app/
RUN mamba install -y --file requirements_general.txt && \
    mamba install -y -c bioconda --file requirements_bioconda.txt && \
    mamba clean --all --yes

# Copy application files
COPY . /app/

# Initialize and install submodule
RUN git submodule update --init --recursive && \
    pip install --no-cache-dir -e /app/sofi_messenger

# Add and set entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Declare volume and expose port
VOLUME /dmx_data
EXPOSE 8000

# Keep container root, drop to appuser at runtime
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
