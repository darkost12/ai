FROM python:3.11-slim

RUN apt-get update

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-k", "gevent", "-b", "0.0.0.0:8000", "app:main"]

CMD ["gunicorn", "-w", "4", "-k", "gevent", "-b", "0.0.0.0:8000", "main:app"]


