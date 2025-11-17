FROM python:3.12-slim

WORKDIR /app

COPY main.py .
COPY pyproject.toml .
COPY README.md .

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]