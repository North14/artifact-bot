FROM python:3.8

RUN mkdir -p /app/data
COPY requirements.txt /app/
COPY artifactbot/ /app/
WORKDIR /app
RUN pip3 install -r requirements.txt

CMD ["python", "/app/main.py"]
