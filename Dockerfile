FROM python:3

RUN mkdir -p /var/vapor
WORKDIR /var/vapor
COPY ./ /var/vapor

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install git+https://github.com/Pycord-Development/pycord.git@33340c705c419af1a7ebc423ca1a60bf0c20b2e5

ENTRYPOINT python /var/vapor/main.py