FROM python:3.12-slim

WORKDIR /app
COPY server.py ./
COPY dist ./

EXPOSE 3000

CMD ["python", "server.py"]
