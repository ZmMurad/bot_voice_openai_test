FROM python:3.10-slim


WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    unzip

COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt


COPY app/ .

CMD ["python","main.py"]

