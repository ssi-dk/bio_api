# syntax=docker/dockerfile:1
FROM condaforge/miniforge3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MONGO_CONNECTION='mongodb://mongo:27017/bifrost_test'

COPY . /app/
WORKDIR /app

RUN mamba install -y --file requirements_general.txt
RUN mamba install -y -c bioconda --file requirements_bioconda.txt

# install the sofi_messenger submodule
RUN git submodule update --init --recursive
RUN pip install -e /app/sofi_messenger

VOLUME /dmx_data

# Document which ports are exposed
EXPOSE 8000

# Start Uvicorn and listen on port
WORKDIR /app
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]