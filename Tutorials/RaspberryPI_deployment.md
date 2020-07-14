## CFFI end-to-end deployment on Raspberry PI (Model 3B) with docker containers

Solution requires:

Raspberry PI 3B (or later) with a clean Ubuntu 64bit Server OS (20.04 tested). NB: Raspbian will not work as currently (as of June 2020) 32bit only and recent MongoDB releases require a 64 bit OS. 

The Raspberry PI will be located on a home network behind a standard home router firewall. Any devices in the home network will be able to access the Internet, but no traffic can enter the network unless firewall rules have been configured on the router. The tutorial includes steps needed to enable firewall rules. The tutorial also assumes your Internet service provider has provisioned a static IP address.

The tutorial will treat the Raspberry PI as headless, and another laptop is required to configure the Raspberry PI at the command line.

### Initial Raspberry PI set up with Operating System ###

1. Recommend a 16GB or larger memory card. From  https://ubuntu.com/download/raspberry-pi download the Ubuntu 20.04 **64bit** LTS image 

2. Using this tutorial, https://ubuntu.com/tutorials/how-to-install-ubuntu-on-your-raspberry-pi#1-overview, burn the image onto a memory card using your laptop. Boot the Raspberry PI and connect remotely in step 4 as the Ubuntu user. NB: For step 4, we are using the headless option.  No need to install the desktop GUI in step 5.

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

    python3 --version

14. However pip3 is not installed. Install it:

    sudo apt install python3-pip

15. As per https://docs.docker.com/engine/install/ubuntu/, remove any older traces of docker and install docker registry and GPG key. Configure the PI to use a stable repository not nightly or test

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

22. Confirm it is available:

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

25. Now pull down Python into the Docker respository. For another day, the alpine version would be better as it is much smaller and lightweight. Alpine is used on the kubernetes google clould tutorial.

    docker pull python

26. Also pull down nginx for the reverse proxy

    docker pull nginx

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

29. Get the cffa and cffadb code and configuration files from git.

    ```shell
    git clone https://github.com/GreyPaperclip/cffa
    git clone https://github.com/GreyPaperclip/cffadb
    ```

30. The storage directory for MongoDO will be mounted from the host OS to the MongoDB container. This is because a container is ephereal and all data is lost when a container is restarted. By mounting an OS directory this ensures data persistence. Provided the host directory exists MongoDB will initialise all files upon first startup.

    ```shell
    sudo mkdir -p /etc/mongoFBdata
    ```

31. Define your MongoDB root username and password. For example:

    ```shell
    export MONGO_ROOT_USERNAME=root
    export MONGO_ROOT_PASSWORD=mongopass
    ```

32. Create a initialization script for MongoDB in $HOME/cffa. This script creates a DB user for CFFA to use. Note down username and password as this is configured in CFFA later on.

    ```shell
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

33. Create self-signed certs for nginx, CFFA and the proxy between nginx and CFFA

    ```bash
    mkdir nginx
    
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:4096 -keyout nginx/nginx-selfsigned.key -out nginix/nginx-selfsigned.crt
    
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:4096 -keyout nginx/cffa-selfsigned.key -out nginx/cffa-selfsigned.crt
    
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:4096 -keyout nginx/nginx-proxy.key -out nginx/nginx-proxy.pem
    ```

34. Create a log directory for nginx and cffa and (for later on) directory used by lets-encrypt to validate certificates

    ```bash
    sudo mkdir /var/log/cffa /var/log/nginx /home/ubuntu/cffa/letsencrypt/verification
    ```

35. Create the reverse proxy configuration file. This will listen on port 80 and 443. All incoming requests will redirect to https. Nginx handles all static directory requests and will cache them instead of flask. NB: Ensure server_name is correct for your domain.

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

36. There is no need to build containers for nginx and MongoDB as the defaults can be used as downloaded. However CFFA container must be built first

    ### Build CFFA container ###

37. Change to the CFFA code directory.

    ```bash
    cd $HOME/cffa/cffa
    ```

38. Create the boot shell script. This is executed once the container has initialised:

    ```bash
    vi boot.sh
    ```

    ```bash
    #!/bin/bash
    source venv/bin/activate
    exec gunicorn -b :5000 --certfile=/home/cffa/certs/cffa-selfsigned.crt --keyfile=/home/cffa/certs/cffa-selfsigned.key --access-logfile - --error-logfile - -w 1 server:app
    ```

    

39. Now create the Dockerfile - this is used to build the container. Note the password on the first RUN line will need changing.

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
    RUN chmod +x boot.sh
    
    ENV PYTHONPATH /home/cffa/cffadb
    ENV FLASK_APP server.py
    
    RUN chown -R cffa:cffa ./
    USER cffa
    
    EXPOSE 5000
    ENTRYPOINT ["./boot.sh"]
    ```

    

40. Build the container. This will take some time.

    docker build -t cffa:latest .

    ### Create the docker-compose configuration yaml and start the services ###

41. Change back to the home cffa directory

    cd $HOME/cffa

42. Create the docker-compose.yaml file. Note files with <> require updating.

    ```yaml
    1. vi docker-compose.yaml
    
       version: "3"
       services:
           database:
               image: 'mongo'
               container_name: 'footballMongoDB'
               hostname: footballDB
               environment:
                   - MONGO_INITDB_DATABASE=<The MongoDB football DB name - check your init-mongo.js >
                   - MONGO_INITDB_ROOT_USERNAME=${MONGO_ROOT_USERNAME}
                   - MONGO_INITDB_ROOT_PASSWORD=${MONGO_ROOT_PASSWORD}
               volumes:
                       - ./init-mongo.js:/docker-entrypoint-initdb.d/init-mongo.js:ro
                       - /opt/mongoFBdata:/data/db
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
                   - /home/ubuntu/cffa/nginx/nginx-selfsigned.crt:/etc/nginx/cert/nginx-selfsigned.crt
                   - /home/ubuntu/cffa/nginx/nginx-selfsigned.key:/etc/nginx/cert/nginx-selfsigned.key
                   - /home/ubuntu/cffa/nginx/nginx-proxy.pem:/etc/nginx/cert/nginx-proxy.pem
                   - /home/ubuntu/cffa/nginx/nginx-proxy.key:/etc/nginx/cert/nginx-proxy.key
                   - /home/ubuntu/cffa/nginx/logs/:/var/log/cffa/
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
               - /home/ubuntu/cffa/cffa/logs:/home/cffa/logs
    ```

    ### Start up the containers ###

43. Start up the containers: 

    docker-compose up -d

44. Check status of the containers, recommend running this several times as it can take a few minutes to start.

    docker ps

    ### Check networking ###

45. Log into your home internet router, and set up port forwarding from the internet on port 80 (http) and port 443 (https) to the ubuntu server IP address (not the containers, docker will route traffic to the reverse proxy)

46. Log into your DNS provider for your domain name, and configure an A record to forward cffa.yourdomain.com to your router external IP address.

47. Open your web browser (on laptop or mobile), and go to cffa.yourdomain.com. If successful you will see the login prompt:

    ![](https://lh3.googleusercontent.com/pw/ACtC-3dBOerh6lT5EpI_pobsP63-EDducO5XoF2pZDt_jEmptzMj9NtIdgU9TMq7k4IXHhWthjfOVT-nxf1Yyf-zYaJ24JZbwM0Y5AbBk5UJLkF1-DktSI12o4Vx3lnXAzKwoi_nEeE81AFATgcBH6gOz4Gp=w1043-h560-no?authuser=0)

48. x

49. y

50. z

    