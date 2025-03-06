# syntax=docker/dockerfile:1
FROM condaforge/miniforge3

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV MONGO_CONNECTION="mongodb://mongo:27017/bifrost_test"
ENV AMQP_HOST="amqp://guest:guest@rabbitmq/"

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

# install the sofi_messenger submodule

RUN git submodule update --init --recursive
RUN ls -la sofi_messenger/
RUN pip install -e /app/sofi_messenger

# Clone cgmlst-dists repository from GitHub
RUN git clone https://github.com/tseemann/cgmlst-dists.git

# Navigate into the cloned repository and build using make
WORKDIR /app/cgmlst-dists
RUN make    

# Go back to the main application directory
WORKDIR /app

# Install Python dependencies via mamba or conda

# Install general Python dependencies first
RUN mamba install -c conda-forge --file /app/requirements_general.txt

# Install bioinformatics-related dependencies from Bioconda
RUN mamba install -c bioconda --file /app/requirements_bioconda.txt

RUN pip install aio-pika==9.3.0

# Create a volume for external data (optional)
VOLUME /dmx_data

# Expose the necessary port (e.g., for a FastAPI or Uvicorn app)
EXPOSE 8000

# so here to test the rabbitMQ i can use the python script?
CMD ["python", "rabbitmq_runner_dockertest.py"]

# Set the entry point to start the app with Uvicorn (if using FastAPI, for example)
#ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

#https://stackoverflow.com/questions/63116838/rabbitmq-doesnt-start-with-docker-compose