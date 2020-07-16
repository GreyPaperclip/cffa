FROM python

RUN useradd -d /home/cffa -m -p thePassword -s /bin/bash cffa

WORKDIR /home/cffa

COPY requirements.txt requirements.txt
RUN python3 -m venv venv
RUN venv/bin/pip3 install -r requirements.txt
RUN venv/bin/pip3 install gunicorn

COPY server.py config.py constants.py formHandler.py importDataFromGoogle.py importExportCFFA.py boot.sh ./
RUN mkdir cffadb
COPY cffadb/__init__.py cffadb/constants.py cffadb/dbinterface.py cffadb/footballClasses.py cffadb/googleImport.py cffadb/setup.py cffadb/README.md ./cffadb/
RUN mkdir templates static logs
RUN mkdir ExportImport
RUN chmod +x boot.sh
RUN mkdir uploads

ENV PYTHONPATH /home/cffa/cffadb
ENV FLASK_APP server.py

RUN chown -R cffa:cffa ./
USER cffa

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
