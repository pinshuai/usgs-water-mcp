FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip \
    && pip install -e .

CMD ["python", "-m", "usgs_water_mcp"]