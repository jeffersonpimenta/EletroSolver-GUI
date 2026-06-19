# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    ELETROGUI_HEADLESS=1

WORKDIR /app

# Dependências primeiro (cache de camada).
COPY pyproject.toml README.md ./
COPY EletroSolver.py Faltas.py ./
COPY gui ./gui

RUN pip install --no-cache-dir .

EXPOSE 8080
CMD ["python", "-m", "gui.main"]
