FROM python:3

RUN mkdir -p /var/vapor
WORKDIR /var/vapor
COPY ./ /var/vapor

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install git+https://github.com/Pycord-Development/pycord

ENTRYPOINT python /var/vapor/main.py