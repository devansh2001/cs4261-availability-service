# This file is taken from official tutorial: https://docs.docker.com/language/python/build-images/
# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

# Using expose: https://dev.to/ejach/how-to-deploy-a-python-flask-app-on-heroku-using-docker-mpc
# EXPOSE 5000

# # https://www.youtube.com/watch?v=4eQqcfQIWXw
CMD [ "python3", "app.py" ]
