FROM python:3.8.3-alpine3.12

RUN addgroup -g 2000 cffa \
&& adduser -S -G cffa -u 2001 -h /home/cffa -s /bin/bash cffa

WORKDIR /home/cffa

COPY requirements.txt requirements.txt
RUN apk add gcc musl-dev python3-dev libffi-dev openssl-dev bash
RUN pip install --upgrade pip
RUN python3 -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn

COPY server.py config.py constants.py formHandler.py importDataFromGoogle.py importExportCFFA.py boot.sh ./
RUN mkdir cffadb
COPY cffadb/__init__.py cffadb/constants.py cffadb/dbinterface.py cffadb/footballClasses.py cffadb/googleImport.py cffadb/setup.py cffadb/README.md ./cffadb/
RUN mkdir logs
RUN mkdir ExportImport uploads
RUN chmod +x boot.sh

ENV PYTHONPATH /home/cffa:/home/cffa/cffadb
ENV FLASK_APP server.py

RUN mkdir shared

RUN chown -R cffa:cffa ./
USER cffa

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
