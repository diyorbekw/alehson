FROM python:3.11

# Ishchi papka
WORKDIR /app

# Tizim paketlarini o'rnatish
RUN apt-get update && apt-get install -y \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Requirements.txt dan kutubxonalarni o'rnatamiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Project fayllarini ko'chiramiz
COPY . .

EXPOSE 8000