FROM python:3.12-rc

WORKDIR /vowifi-geoblocking-scan-epdgs

COPY main.py .
COPY requirements.txt .
#COPY venv/ ./venv/

RUN apt-get update
RUN apt-get install -y build-essential
RUN apt-get install -y python3-dev
RUN apt-get install -y swig
RUN apt-get install -y libpcsclite-dev

RUN set -ex;\
    pip install -r requirements.txt

RUN set -ex;\
    chmod a+x main.py

CMD ["/vowifi-geoblocking-scan-epdgs/main.py"]
#ENTRYPOINT ["/bin/sh"]
