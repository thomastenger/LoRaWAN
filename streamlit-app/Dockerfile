FROM python:3.10-slim

# Installer dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installer dépendances Python
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir streamlit grpcio chirpstack-api psycopg2-binary


# Port exposé
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
