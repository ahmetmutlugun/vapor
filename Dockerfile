FROM python:3

RUN mkdir -p /var/vapor
WORKDIR /var/vapor
COPY ./ /var/vapor

RUN pip install git+https://github.com/Pycord-Development/pycord
RUN pip install requests

ENTRYPOINT python /var/vapor/main.py