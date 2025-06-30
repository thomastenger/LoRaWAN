FROM python:3.11-slim

WORKDIR /app

# Copie des dépendances et installation
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code
COPY app.py ./

# Lancement Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]
