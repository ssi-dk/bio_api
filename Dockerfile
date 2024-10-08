# syntax=docker/dockerfile:1
FROM condaforge/miniforge3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MONGO_CONNECTION='mongodb://mongo:27017/bifrost_test'

COPY . /app/
WORKDIR /app

RUN mamba install --file requirements_general.txt
RUN mamba install -c bioconda --file requirements_bioconda.txt

VOLUME /dmx_data

# Document which ports are exposed
EXPOSE 8000

# Start Uvicorn and listen on port
WORKDIR /app
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]