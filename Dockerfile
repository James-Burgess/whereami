FROM python:3.8-buster
ENV PYTHONUNBUFFERED=1

RUN apt-get update -y

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY ./app /app

ENTRYPOINT [ "python3" ]

CMD [ "api.py" ]
