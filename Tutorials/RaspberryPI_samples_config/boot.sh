#!/bin/bash
source venv/bin/activate
exec gunicorn -b :5000 --certfile=/home/cffa/certs/cffa-selfsigned.crt --keyfile=/home/cffa/certs/cffa-selfsigned.key --access-logfile - --error-logfile - -w 1 server:app
