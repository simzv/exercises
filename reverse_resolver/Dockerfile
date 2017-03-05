FROM ubuntu:16.04

RUN  apt-get update \
    && apt-get -y upgrade \
    && useradd --base-dir /var/lib --create-home --shell /bin/bash app \
    && apt-get -y install python \
        python-setuptools \
        python-pip \
        whois

COPY *.py /var/lib/app/
COPY requirements.txt /var/lib/app/

RUN chown app:app /var/lib/app/* \
    && pip install --upgrade setuptools pip \
    && cd /var/lib/app/ \
    && pip install -r requirements.txt \
    && apt-get -y autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

WORKDIR /var/lib/app

USER app

ENTRYPOINT ["/usr/bin/python"]

CMD ["main.py"]

EXPOSE 8080
