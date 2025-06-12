FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir locust

COPY locustfile.py .

EXPOSE 8089

CMD ["locust", "--host=http://nginx", "--web-host=0.0.0.0"]