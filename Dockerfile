FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini requirements.txt ./
RUN pip install --upgrade pip \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY src ./src
COPY migrations ./migrations
COPY evals ./evals

RUN pip install --no-deps .

EXPOSE 8000

CMD ["uvicorn", "agent_mentor.main:app", "--host", "0.0.0.0", "--port", "8000"]
