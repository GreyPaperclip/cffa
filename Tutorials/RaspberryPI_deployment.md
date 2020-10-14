## CFFA end-to-end deployment on Raspberry PI (Model 3B) with docker containers

Solution requires:

Raspberry PI 3B (or later) with a clean Ubuntu 64bit Server OS (v20.04 tested). NB: Raspbian will not work as currently (as of June 2020) as this is a 32bit OS and recent MongoDB releases require a 64 bit OS. 

The Raspberry PI will be located on a home network behind a standard home router firewall. Any devices in the home network will be able to access the Internet, but no traffic can enter the network unless firewall rules have been configured on the router. The tutorial includes details needed to enable firewall rules. The tutorial also assumes your Internet service provider has provisioned your router with an static internet IP address.

The tutorial will treat the Raspberry PI as headless, and another laptop is required to configure the Raspberry PI at the command line.

The tutorial covers the use of self-signed certificates however  Appendix 1 includes steps needed to use signed certificates by LetsEncrypt/certbot.

The tutorial steps will be very similar, if not the same, on a traditional x86 server (or compute instance in the cloud) with Ubuntu installed.

#### Assumptions ####

This tutorial requires the user to have basic understanding of Unix/Linux, Raspberry installation and use of the vi text editor. Alternative text editors such as emacs or nano can be substituted when the vi command is quoted.

## Architecture ##

![](https://lh3.googleusercontent.com/pw/ACtC-3eKji3yiy9ysWPbaFsoMoz0Txb_a96heJVV452z0fTABeaJz6KQoH6_-b83CijxOtCSntGvO2wCFf972ETh0c8l3AgZ2MaovtK918JNeiJIne1mt6SCcNVZRxWfx2b5ozhRTZKVkiakblCC_qWn8g4c=w864-h612-no)

### Initial Raspberry PI set up with Operating System ###

1. I recommend a 16GB or larger memory card. From  https://ubuntu.com/download/raspberry-pi download the Ubuntu 20.04 **64bit** LTS image 

2. Using this tutorial, https://ubuntu.com/tutorials/how-to-install-ubuntu-on-your-raspberry-pi#1-overview, burn the image onto a memory card using your laptop. Boot the Raspberry PI and connect remotely in step 4 as the Ubuntu user. NB: For step 4, we are using the headless option.  There is no need to install the desktop GUI in step 5.

   * As the Raspberry PI will be a webserver it is recommended to use a cabled ethernet connection instead of wi-fi as this will be more stable.

   #### Update OS and set static IP

3. Update the apt utility

   ```shell
   sudo apt update
   ```

4. Update the OS, this may take some time.

   ```shell
   sudo apt upgrade
   ```

5. Check network interfaces. Likely eth0 or eno1 will be the interface.

   ```shell
   ip a
   ```

6. Use netplan to check interface - if wired should show speed such as 1000Mb/s

   ```shell
   sudo ethtool eth0
   ```

7. Configure a netplan yaml to set IP address/subnet, gateway and name server (usually your internet router). For example for an IP address for 192.168.0.57 where the subnet is from 192.168.0.0 to 192.168.0.255 use the following

   ```shell
   sudo vi /etc/netplan/99_config.yaml
   ```

   ```yaml
   network:
           version: 2
           renderer: networkd
           ethernets:
                           eth0:
                                   addresses:
                                           - 192.168.0.57/24
                                   gateway4: 192.168.0.254
                                   nameservers:
                                                   search: [mydomain, otherdomain]
                                                   addresses: [192.168.0.254]
   ```

8. Apply the netplan so that the IP address is set at reboot

   ```shell
   sudo netplan apply
   ```

9. Set the hostname for the server, e.g for football server:

   ```shell
   sudo hostnamectl set-hostname footballserver
   ```

10. Then edit the hosts file and add the record for football server:

    ```shell
    sudo vi /etc/hosts
    ```

    ```asn.1
    127.0.0.1 localhost
    192.168.1.57 footballserver
    
    # The following lines are desirable for IPv6 capable hosts
    
    ::1 ip6-localhost ip6-loopback
    fe00::0 ip6-localnet
    ff00::0 ip6-mcastprefix
    ff02::1 ip6-allnodes
    ff02::2 ip6-allrouters
    ff02::3 ip6-allhosts
    ```

11. Reboot to apply changes

    ```shell
    sudo reboot
    ```

    ### Install software components - pip3, docker and docker-compose, and pull down docker images. ###

12. Log back in again (as ubuntu) with ssh

13. Ubuntu 20.04 has python3 already installed. Check this with 

    ```bash
    python3 --version
    ```

14. However pip3 is not installed. This is required for docker-compose later on. Install it:

    ```bash
    sudo apt install python3-pip
    ```

15. As per https://docs.docker.com/engine/install/ubuntu/, remove any older traces of docker and install docker registry and GPG key. Configure the Raspberry Pi to use a stable repository instead nightly or test

    ```shell
    sudo apt-get remove docker docker-engine docker.io containerd runc
    ```

    ```shell
    sudo apt update
    ```

    ```shell
    sudo apt-get install \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg-agent \
        software-properties-common
    ```

    ```shell
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    ```

    ```shell
    sudo add-apt-repository \
       "deb [arch=arm64] https://download.docker.com/linux/ubuntu \
       $(lsb_release -cs) \
       stable"
    ```

16. Install latest version of docker engine:

    ```shell
     sudo apt-get update
     sudo apt-get install docker-ce docker-ce-cli containerd.io
    ```

17. Check docker installed successfully by testing hello-world:

    ```shell
    sudo docker run hello-world
    ```

18. Follow https://docs.docker.com/engine/install/linux-postinstall/ and configure ubuntu user to run docker commands, i.e:

    ```shell
    sudo groupadd docker
    sudo usermod -aG docker $USER
    ```

19. Log out and log back in to apply the changes in the previous step.

20. Configure docker to start on boot:

    ```shell
    sudo systemctl enable docker
    ```

21. Pull down MongoDB into the docker repository

    ```shell
    docker pull mongo
    ```

22. Confirm it is available under listed images:

    ```shell
    docker images
    ```

23. Install docker-compose and dependancies:

    ```shell
    sudo apt install --yes python3-paramiko
    sudo pip3 install docker-compose
    ```

24. Check docker-compose version:

    ```shell
    docker-compose --version
    ```

25. Now pull down Python into the Docker respository. For another day, the alpine version would be better as it is much smaller and lightweight. Alpine is used on the kubernetes google cloud tutorial.

    ```shell
    docker pull python
    ```

26. Pull down nginx for the reverse proxy

    ```shell
    docker pull nginx
    ```

    ### Get CFFA files, pre-configure MongoDB and certs ###

27. Make sure you are at the Ubuntu home directory

    ```shell
    cd $HOME
    ```

28. Create cffa directory and move into it

    ```shell
    mkdir cffa 
    cd cffa
    ```

29. Get the cffa and cffadb code and configuration files from GitHub. cffadb wil be located inside cffa.

    ```shell
    git clone https://github.com/GreyPaperclip/cffa
    cd cffa
    git clone https://github.com/GreyPaperclip/cffadb
    ```

30. The storage directory for MongoDB will be mounted from the host OS to the MongoDB container. This is because a container is ephereal and all data is lost when a container is restarted. By mounting an OS directory this ensures data persistence. Provided the host directory exists MongoDB will initialise all files upon first startup.

    ```shell
    sudo mkdir -p /opt/mongoCFFA
    ```

31. Define your own MongoDB root username and password as required by the MongoDB container when starting up. For example:

    ```shell
    export MONGO_ROOT_USERNAME=root
    export MONGO_ROOT_PASSWORD=mongopass
    ```

32. Create a initialization script for MongoDB in $HOME/cffa. This script creates a DB user for CFFA to use. Note down username and password as this is configured in CFFA later on. The example file is also provided in the tutorial directory as downloaded during git clone earlier.

    ```shell
    cd $HOME/cffa
    vi init-mongo.js
    ```

    ```javascript
    db.createUser(
    	{
    		user : "footballdba",
    		pwd : "lineker1990",
    		roles : [
    			{
    				role: "readWrite",
    				db: "footballDB"
    			}
    		]
    	}
    )
    ```

33. Create self-signed certs for nginx, CFFA and the proxy between nginx and CFFA. Each cert request will prompt for details on location, server name and email details. As CFFA runs as non-root, we change permissions to read for the two CFFA cert files.

    ```bash
    mkdir nginx certs
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:4096 -keyout certs/nginx-selfsigned.key -out certs/nginx-selfsigned.crt
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:4096 -keyout certs/cffa-selfsigned.key -out certs/cffa-selfsigned.crt
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:4096 -keyout certs/nginx-proxy.key -out certs/nginx-proxy.pem
    sudo chmod a+r certs/cffa-selfsigned.key certs/cffa-selfsigned.crt
    ```

34. Create a log directory for nginx and cffa and (for later on) directory used by lets-encrypt to validate certificates. NB: creation by root is intentional as nginx runs as root (it has to in order to listen on ports smaller than 1024).

    ```bash
    mkdir log log/cffa
    sudo mkdir letsencrypt log/nginx letsencrypt/verification
    ```

35. Create the reverse proxy configuration file. This will listen on port 80 and 443. All incoming requests will redirect to https. Nginx handles all static directory requests and will cache them instead of flask. NB: Ensure server_name is correct for your domain. Note all paths are in the container, not on the ubuntu server as currently seen. Later on these directories will be 'mounted' so nginx can load the certifications and create logs in the cffa directories.

    ```bash
    vi nginx/reverse_proxy.conf
    ```

    ```nginx
    server {
        # listen on port 80 (http)
        listen 80;
        server_name cffa.yourdomainname.com;
        location ~ /.well-known {
           root /etc/nginx/letsencrypt/verification;
        }
        location / {
            # redirect any requests to the same URL but on https
            return 301 https://$host$request_uri;
        }
    }
    server {
    
        # listen on port 443 (https)
        listen 443 ssl;
        server_name _;
    
        # location of the self-signed SSL certificate
        ssl_certificate /etc/nginx/cert/nginx-selfsigned.crt;
        ssl_certificate_key /etc/nginx/cert/nginx-selfsigned.key;
        
        # write access and error logs to /var/log
        access_log /var/log/cffa/cffa_access.log;
        error_log /var/log/cffa/cffa_error.log;
        
        location / {
            # forward application requests to the gunicorn server
            proxy_pass https://cffa_flask:5000;
        proxy_ssl_certificate /etc/nginx/cert/nginx-proxy.pem;
        proxy_ssl_certificate_key /etc/nginx/cert/nginx-proxy.key;
        proxy_ssl_trusted_certificate /etc/nginx/cert/cffa-selfsigned.crt;
        proxy_ssl_session_reuse on;
            proxy_redirect off;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
        
        location /static {
            # handle static files directly, without forwarding to the application
            alias /opt/cffa/static;
            expires 30d;
        }
    }
    ```

36. There is no need to build containers for nginx and MongoDB as the defaults can be used as downloaded. The CFFA container must be built before docker-compose is used to orchestrate deployment.

    ### Build CFFA container ###

37. Change to the CFFA code directory.

    ```bash
    cd $HOME/cffa/cffa
    ```

38. Create the boot shell script. This is executed once the container has initialised. The boot.sh script is also included as part of the cffa GitHub download.

    ```bash
    vi boot.sh
    ```

    ```bash
    #!/bin/bash
    source venv/bin/activate
    exec gunicorn -b :5000 --certfile=/home/cffa/certs/cffa-selfsigned.crt --keyfile=/home/cffa/certs/cffa-selfsigned.key --access-logfile - --error-logfile - -w 1 server:app
    ```

39. Now create the Dockerfile - this is used to build the container. Note the password on the first RUN line should be changed.

    ```bash
    vi Dockerfile
    ```

    ```dockerfile
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
    RUN mkdir uploads
    RUN chmod +x boot.sh
    
    ENV PYTHONPATH /home/cffa/cffadb
    ENV FLASK_APP server.py
    
    RUN chown -R cffa:cffa ./
    USER cffa
    
    EXPOSE 5000
    ENTRYPOINT ["./boot.sh"]
    ```

40. Build the container. This will take some time - circa 15 minutes on a Raspberry PI 3B. Don't forget the full stop at the end of the command.

    ```bash
    docker build -t cffa:latest .
    ```

    You can review the image. Docker will also list nginx, python and mongo images.

    ```bash
    docker images
    ```

    ### Create the docker-compose configuration yaml and start the services ###

41. Change back to the home cffa directory

    ```bash
    cd $HOME/cffa
    ```

42. Create the docker-compose.yaml file. Note settings with <> require updating. The sample is available in the tutorial directory as well. 

    ```bash
    vi docker-compose.yaml
    ```

    ```yaml
    # docker-compose.yaml
    version: "3"
    services:
        database:
            image: 'mongo'
            container_name: 'footballMongoDB'
            hostname: footballDB
            environment:
                - MONGO_INITDB_DATABASE=<The MongoDB football DB name - check your init-mongo.js db setting >
                - MONGO_INITDB_ROOT_USERNAME=${MONGO_ROOT_USERNAME}
                - MONGO_INITDB_ROOT_PASSWORD=${MONGO_ROOT_PASSWORD}
            volumes:
                    - ./init-mongo.js:/docker-entrypoint-initdb.d/init-mongo.js:ro
                    - /opt/mongoCFFA:/data/db
            ports:
                    - '27017-27019:27017-27019'
        reverseproxy:
            container_name: reverse
            hostname: reverse
            image: nginx:latest
            ports:
                - 80:80
                - 443:443
            volumes:
                - /home/ubuntu/cffa/letsencrypt/verification/:/etc/nginx/letsencrypt/verification/
                - /home/ubuntu/cffa/nginx/reverse_proxy.conf:/etc/nginx/conf.d/default.conf
                - /home/ubuntu/cffa/certs/nginx-selfsigned.crt:/etc/nginx/cert/nginx-selfsigned.crt
                - /home/ubuntu/cffa/certs/nginx-selfsigned.key:/etc/nginx/cert/nginx-selfsigned.key
                - /home/ubuntu/cffa/certs/nginx-proxy.pem:/etc/nginx/cert/nginx-proxy.pem
                - /home/ubuntu/cffa/certs/nginx-proxy.key:/etc/nginx/cert/nginx-proxy.key
                - /home/ubuntu/cffa/log/nginx:/var/log/cffa/
                - /home/ubuntu/cffa/cffa/static:/opt/cffa/static
    
        cffa_flask:
            container_name: cffa_flask
            hostname: cffa_flask
            image: cffa:latest
            # to debug if flask stops on start entrypoint: ["sh", "-c", "sleep 2073600"]
            ports:
                - 8000:5000
            environment:
                - SECRET_KEY=<a string to encrypt data by flask>
                - AUTH0_CLIENT_ID=<your Client ID for CFFA app>
                - AUTH0_DOMAIN=<your Auth0 Domain>
                - AUTH0_CLIENT_SECRET=<Your Client Secret for CFFA app>
                - AUTH0_CALLBACK_URL=<Your Client callback URL as configured in the Auth0 app configuration screen>
                - AUTH0_AUDIENCE=<Your Audience URL at Auth0>
                - BACKEND_DBPWD=<The MongoDB football DB password - check your init-mongo.js>
                - BACKEND_DBUSR=<The MongoDB football username - check your init-mongo.js>
                - BACKEND_DBHOST=database
                - BACKEND_DBPORT=27017
                - BACKEND_DBNAME=<The MongoDB football DB name - check your init-mongo.js >
                - EXPORTDIRECTORY=/home/cffa/cffa/ExportImport
          volumes:
                - /home/ubuntu/cffa/cffa/static:/home/cffa/static
                - /home/ubuntu/cffa/cffa/templates:/home/cffa/templates
                - /home/ubuntu/cffa/log/cffa:/home/cffa/logs
                - /home/ubuntu/cffa/certs/cffa-selfsigned.crt:/home/cffa/certs/cffa-selfsigned.crt
                - /home/ubuntu/cffa/certs/cffa-selfsigned.key:/home/cffa/certs/cffa-selfsigned.key
    ```

    ### Start up the containers ###

43. Start up the containers: 

    ```shell
    docker-compose up -d
    ```

44. Check status of the containers, recommend running this several times as it can take a few minutes to start.

    ```shell
    docker ps
    ```

    ### Check networking ###

45. Log into your home internet router, and set up port forwarding from the internet on port 80 (http) and port 443 (https) to the ubuntu server IP address (not the containers, docker will route traffic to the reverse proxy)

46. Log into your DNS provider for your domain name, and configure an A record to forward cffa.yourdomain.com to your router external IP address.

47. Open your web browser (on laptop or mobile), and go to cffa.yourdomain.com. As self-signed certificates are being used you will need to authorised the browser to visit the website.

    ![](https://lh3.googleusercontent.com/pw/ACtC-3fkbv4VFClM8dmkymD0nL5IBkiAEs0Sxec1G3mzSDWeEyZkGgLK2XrHpFVVQdUiyLsPVRcOYIvM_5qqnEsN94H15MpRsRzkM9vyTBbdu00sDe491R7Y0yFPedKW0vttZdBAEy6WjwsrnPD-ao1L7jve=w780-h370-no)

48.  Fingers crossed you will now see the login prompt:

    ![](https://lh3.googleusercontent.com/pw/ACtC-3fSmp7A7M_0S6odC5mbar6u38Bvph12KuaC0VOH5RF67CmTgrpFLWrw2oQJdoZVEPObHSd3xTBkWOXgE1wFTzErnGTX8ch_5Jv_XN0tc0zG3B4dJknGHTmnMThXnR2GVspjQQaklp9N0pKJc6JX3Kef=w1043-h560-no)

    ### Shutdown and clean up ###

    49. To shut down the docker containers, execute:

        ```bash
        docker-compose stop
        ```

    50. To remove the stored docker images for nginx, cffa and mongo

        ```bash
        docker image rm cffa:latest
        docker image rm nginx:latest
        docker image rm mongo:latest
        ```

    52. To remove cffa completely (be careful):

        ```bash
        sudo rm -rf /home/ubuntu/cffa
        sudo rm -rf /opt/mongoCFFA
        ```

    ### Troubleshooting ###

    1. Running docker-compose up -d shows the following error:

       ```
       ERROR: The Compose file './docker-compose.yaml' is invalid
       ```

    Use an online yaml checker - yaml is sensitive to white space and alignment. Careful not to paste your

    Auth0 secrets online though!

    2. Containers are terminating   soon after running docker-compose up -d:

    Use docker logs <container_name> to view logs, for example:

    ```bash
    docker logs cffa_flask
    ```

    There could be many many reasons for this. For example:

    a) cffa_flask log shows:

    ```
    PermissionError: [Errno 13] Permission denied: '/home/cffa/logs/cffa_webserver.log'
    ```

     indicates that the  /home/ubuntu/cffa/log/cffa does not have write permissions on the raspberry PI, or perhaps the disk is full.

    b) cffa_flask log shows:

    ```
    Traceback (most recent call last):
      File "/home/cffa/venv/lib/python3.8/site-packages/gunicorn/workers/sync.py", line 129, in handle
        client = ssl.wrap_socket(client, server_side=True,
      File "/usr/local/lib/python3.8/ssl.py", line 1402, in wrap_socket
        context.load_cert_chain(certfile, keyfile)
    PermissionError: [Errno 13] Permission denied
    ```

    Cause: The certificate in /home/ubuntu/cffa/certs for cffa do not have the right read permissions

    c) cffa_flask log shows:

    ```
    Traceback (most recent call last):
      File "/home/cffa/venv/lib/python3.8/site-packages/gunicorn/workers/sync.py", line 129, in handle
        client = ssl.wrap_socket(client, server_side=True,
      File "/usr/local/lib/python3.8/ssl.py", line 1402, in wrap_socket
        context.load_cert_chain(certfile, keyfile)
    IsADirectoryError: [Errno 21] Is a directory
    ```

    Cause: the certificate files are appearing as directories in the container. Check the path of the mounted directory for your certificate file in docker-compose.yaml for validity.
    
    
   ## Appendix 1: Use certified ssl certificates. ##

   Websites should use signed SSL certificates for https communications. Self-signed certificates are fine for development but certification is a necessary step towards a production deployments..  LetsEncrypt/certbot provides a free signed certificiates using the existing nginx configuration deployed with CFFA.

   Back on step 34, we create a directory for letsEncrypt. LetsEncrypt/certbot uses this directory to place a test file via nginx in order to confirm that you have control over the domain in use.

   The process is consists of two steps:

   a) Execute certbot to obtain the certified certificate, 

   b) Apply the signed certificate to cffa flask (boot.sh). This requires updates to the docker-compose deployment yaml which means a service interruption. It is not necessary to update nginx as nginx only redirects http port 80 traffic to use https against flask. Flask, in this deployment still executes all decryption.

   ** Note: In many cases a reverse proxy decrypts all traffic and communication between the proxy and flask would be unencrypted http. This reduces CPU load on the gunicorn flask server. However I encountered an issue with Auth0 integration failing if nginx executed the decryption instead of flask. This requires further investigation.**

   Note that LetsEncrypt certificates expire after 3 months, so certbot needs to be execute to regenerate licenses on a regular basis. For more information go to https://letsencrypt.org

   ### Steps to create and install signed certificates. ###

   1) Shutdown the docker containers and install certbot
    
   ```bash
    cd $HOME/cffa
    docker-compose down
    sudo apt-get install certbot
   ```

   2) Execute certbot to generate the signed certificate for your domain. make sure the -d option is updated for your circumstances.
    
   ```bash
    sudo certbot certonly --webroot -w /home/ubuntu/cffa/letsencrypt/verification -d cffa.mydomain.com
   ```

   3) The certificates will be created in the directory below (replace mydomain with your domain).
    
   ```bash
    sudo ls -la /etc/letsencrypt/live/cffa.mydomain.com
   ```

   4) cffa_flask executes as a non-root user and this requires the private key. The private key is restricted to root by default. In this example we will enable read access but this is unadvisable in a production system. In practice it would be better to restrict the private key to the container only
    
   ```bash
    sudo chmod a+r /etc/letsencrypt/archive/cffa.mydomain.com/privkey1.pem
   ```

   5) Update the boot.sh script to use the signed certificates.
    
   ```bash
    vi $HOME/cffa/cffa/boot.sh
   ```
   
   ```bash
    #!/bin/bash
    source venv/bin/activate
    exec gunicorn -b :5000 --certfile=/home/cffa/certs/cffa-signed.crt --keyfile=/home/cffa/certs/cffa-signed.key --access-logfile - --error-logfile - -w 1 server:app
   ```
   
   6) cffa_flask requires these keys and the location of these keys will be mounted when the cffa_flask container starts. Add the following two volumes to the $HOME/cffa/docker-compose.yaml file under the cffa_flask volumes section:
    
                - /etc/letsencrypt/archive/cffa.mydomain.com/fullchain1.pem:/home/cffa/certs/cffa-signed.crt
                - /etc/letsencrypt/archive/cffa.mydomain.com/privkey1.pem:/home/cffa/certs/cffa-signed.key
   
   7) Rebuild the cffa container:
    
   NB: When building docker containers it is recommended to use versioning instead of cffa:latest, eg: cffa:0.0.1 For purposes of this tutorial this is sufficient for now but this tutorial could be improved in the future. 
    
    ```bash
    cd $HOME/cffa/cffa
    docker build -t cffa:latest .
    ```
    
   8) Now start up the containers again:
    
    ```bash
    cd $HOME/cffa
    docker-compose up -d
    ```
    
   9) If there are any issues with the certificates, it is likely flask will abort and the container will be shutdown. Use '`docker ps`' and '`docker logs cffa_flask`' to determine if the start up was successful
    
   10) Once logged into CFFA, click on the padlock symbol in the URL bar to review the certificate in detail.
    
   ![](https://lh3.googleusercontent.com/pw/ACtC-3eHBFHUZQzm_gGM3pf_wWJIsmvTxMaxBeTt9bD2KFtzzaLcTUa6rc_7b8Xr56wy0UtuO-9pvlmc71dSNKz48UP_IErzBq8Gf2vmBFNMOEfM9-4U27pQytV1Td2vkCwMmLFPiBp4kt8EWQwqnJSrRH5f=w584-h583-no)


​    

​    

   ### Appendix 2. Auth0 Configuration
    
   CFFA integrates with Auth0 and this requires a free-tier account. Go to auth0.com, and sign up for the region you are located (eg: EU or US). CFFA requires a "single page application" application to be created. To do this go to the Applications on the menu on the left hand side and Create Application:
    
   ![](https://lh3.googleusercontent.com/pw/ACtC-3c_RMFdM0Pp_R8UPAy5Wwp6HaDeo1ZRIykZ_xkVc_fCDXhbLvORQWyF_tRciFEQU02xRr6AhiwnPic3PiWKdxUI350yvZjvFGHlZpLSAcAO1UDsghVMu2ykCq9GAcmuK8vsQKb9R3Nuop4OQtkmgsva=w613-h521-no)


​    

   Under the QuickStart tab, enter python as the Regular Web App. Auth0 will now provide lots of information on how Auth0 can be integrated. CFFA follows these content.
    
   Switch to the Settings tab to confirm your Domain, Client ID, Client Secret settings. These are required in step 42 when configuring the compose-docker.yaml file environment variables. 
    
   The Application URIs for Login, Callback and Logout should be configured and saved. These will be based on your domain name, eg:
    
   Application login URI
    
   ```
    https://cffa.mydomain.com/authorize
   ```
    
   Allowed Callback URLs
    
   ```
    https://cffa.mydomain.com/callback
   ```
    
   Allowed Logout URLs
    
   ```
    https://cffa.mydomain.com
   ```
    
   No further Auth0 configuration should be required.


​    