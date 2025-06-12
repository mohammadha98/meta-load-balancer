FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install nginx for the reload command
RUN apt-get update && apt-get install -y nginx && apt-get clean

EXPOSE 8000

CMD ["python", "app.py"]