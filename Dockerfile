FROM ghcr.io/lehigh-university-libraries/python3.13:main@sha256:58c4109c4e7bef9477eef0c337357f037335703176cb786ec4d12d9cd56dfbaa

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
