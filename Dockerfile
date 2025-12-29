FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . /app

RUN python manage.py makemigrations \
    && python manage.py migrate

EXPOSE 7070

CMD ["python", "manage.py", "runserver", "0.0.0.0:7070"]
