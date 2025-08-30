FROM python:3.11

# ishchi papka
WORKDIR /app

# requirements.txt dan kutubxonalarni o‘rnatamiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# project fayllarini ko‘chiramiz
COPY . .

EXPOSE 8000
