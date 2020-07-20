#!/bin/bash
echo "Activating virtual environment"
source venv/bin/activate
echo "Home Directory listing"
ls /home/cffa
echo "Shared directory tree"
ls -ltR /home/cffa/shared
echo "Creating soft links to shared"
ln -s shared/templates templates
ln -s shared/static static
echo "Starting gunicorn"
exec gunicorn -b :5000 --certfile=/home/cffa/shared/certs/cffa-selfsigned.crt --keyfile=/home/cffa/shared/certs/cffa-selfsigned.key --log-level=debug --preload --access-logfile - --error-logfile - -w 1 server:app
