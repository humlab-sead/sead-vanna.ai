
FROM debian:12

RUN apt-get update

RUN apt-get install -y git curl nano python3 pip python3.11-venv postgresql-client postgresql-common libpq-dev

RUN useradd -m vanna

RUN python3 -m venv /home/vanna/pyenv

WORKDIR /home/vanna/

COPY requirements.txt /home/vanna/

RUN /home/vanna/pyenv/bin/pip install -r requirements.txt

CMD /home/vanna/pyenv/bin/python ./app/app.py
