FROM ghcr.io/lehigh-university-libraries/python3.13:main@sha256:fcfc16365eab3c32ff4d7136e9be75d8bbf7579f170ed8bda0aff65624dc2929

WORKDIR /app

COPY requirements.txt /app
RUN uv pip install \
   --break-system-packages \
   --system \
   -r /app/requirements.txt

COPY . /app

ENV FLASK_APP=app:app \
    HOME=/tmp \
    PORT=5000
