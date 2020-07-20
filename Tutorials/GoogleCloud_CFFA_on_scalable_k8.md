# CFFA end-to-end scalable deployment with CentOS with Google Compute and Kubernetes service. #

### Pre-requisites ###

a) Laptop to execute gcloud commands remotely. Tutorial uses a google compute instance to build the CFFA docker container and execute deployment. During Appendix 2, it highlights that all these steps can actually be executed on your laptop, instead of provisioning a google compute instance, at some point I may write a sister Tutorial to cover this end-to-end.

b) Ownership of a Domain Name. During the tutorial, DNS records will require an A record created/updated to point to the ingress IP of the kubernetes cluster.

c) This Tutorial covers self-signed certificates set up. LetsEncrypt/certbot step to configure signed certificates may follow in the future.

d) A google cloud account. For new users there is a $300 credit. The tutorial may cost £5-£10 depending on how long it takes to complete and how long CFFA is running. Note that images and data provisioned will incur charges if when not used. Ensure that the teardown steps are completed at the end to minimise your costs.

Note: The tutorial focusses exclusively on using the gcloud sdk command line. Although many of the steps are possible using the google web GUI, familiarization of gcloud will help you make more effective use of their cloud services.

### Assumptions ###

The tutorial requires the user to have basic understanding of Unix/Linux, and use of the vi text editor. However alternative text editors such as emacs or nano can be substituted when the vi command is quoted.

### Credits ###

MongoDB deployment based on http://pauldone.blogspot.com/2017/06/deploying-mongodb-on-kubernetes-gke25.html

CFFA Flask implementation used https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world as inspiration

Google Cloud documentation.

## Architecture ##

Diagram to follow

## Install gcloud sdk and start compute instance for container build

1. If not already, sign up to google cloud at https://cloud.google.com  (click on "Get started for free"). The free trial will ask for your details including credit card to quality for the free $300.

2. Follow the google clould quickstart for your laptop and install gcloud: https://cloud.google.com/sdk/docs/quickstarts

3. First step is to initiate gcloud, if not already via the above quickstart. The init will require gcloud login/confirmation and confirmation of default settings.

   ```bash
   gcloud init
   ```

4. create a project for CFFA, for example:

   ```bash
   gcloud projects create cffa-scalable --name cffa
   ```

5. Check available projects and confirm creation:

   ```bash
   gcloud projects list
   ```

6. A project must be associated with a billing account. This can be done via the GUI. Log into the Console at https://console.cloud.google.com and ensure the cffa project is selected on the pull down. Select the Billing option from the top left of the screen.

   ![Billing](https://photos.google.com/share/AF1QipME0k3nhZs8ZwdagNPQxM6x7lUZL7kAnQledXBABHHUxvE2GK9E5qvF348JuPruUw/photo/AF1QipO53HWtcEahg4SShK2gFhEaGYL9GwrAFSw_NQnM?key=R095SWJ3dGFuOFBIUEYxUl9mR2RfemtnRm0xVTRB)

7. Link to the billing account (there should be one created when you signed up to google)

8. Set up gcloud kubectl so we can configure kubernetes, and set authorisation (google will prompt you to log into a URL to confirm identity) and set intended zone. For the appropriate zone check: https://cloud.google.com/compute/docs/regions-zones

   ```bash
   gcloud components install kubectl
   gcloud auth application-default login
   gcloud config set compute/zone europe-west2-b
   ```

9. We will use the public Centos image for our container. Use the followling command to see available images. The first time this command is run it will enable the compute APIs so may take a few minutes to complete.

   ```bash
   gcloud compute images list
   ```

   ```
   NAME                     PROJECT              FAMILY             DEPRECATED  STATUS
      centos-6-v20200714    centos-cloud         centos-6                       READY
      centos-7-v20200714    centos-cloud         centos-7                       READY
      centos-8-v20200714    centos-cloud         centos-8                       READY
      cos-69-10895-385-0    os-cloud            cos-69-lts                      READY
      cos-73-11647-600-0    cos-cloud            cos-73-lts                     READY
      ....
   ```

   We will use centos-7 as MongoDB is not yet supported on Centos-8.

10. Set the project, your compute zone and then check available machine times.

    gcloud config set project cffa-scalable
    gcloud config set compute/zone europe-west2-b

    gcloud compute machine-types list | grep europe-west2-b

11. Create the instance using the e2-small (2 CPU, 2GB RAM) . When prompted select your location. For more information: https://cloud.google.com/compute/docs/regions-zones

    ```bash
    gcloud compute instances create cffa-builder --image-family centos-7 --image-project centos-cloud --machine-type e2-small --create-disk size=16,type=pd-ssd
    ```

    Note: the instance name, cffa-builder, must all be lower-case. If this command is successful it will show it is running with internal and external IP addresses.

12. Now connect to the instance. Update the command to use the zone you specified.:

    ```bash
    gcloud compute ssh --project cffa-scalable --zone europe-west2-b cffa-builder
    ```

    NB: First time you connect to a gcloud instance you will be prompted for the ssh password.

    ### Install docker and kubectl on cffa-builder ###

13. We will use  kubectl to control the google kubernetes cluster - these need to be installed.  yum-untils is required to add repos via yum-config-manager and git is required to get CFFA source onto the server.

    ```bash
    sudo yum install -y yum-utils
    sudo yum install kubectl
    sudo yum install git
    ```

14. Now configure gcloud on the cffa-builder server and prep for kubernetes. When prompted for an accoutn during init, do not use the compute service account but instead create a new configuration. You then will need to log into your google account with a URL when prompted. Set the project to cffa-scalable and set your preferred compute zone. When running the Auth command, another URL needs to be pasted into the browser to confirm authorisation. 

    ```bash
    gcloud init
    gcloud auth application-default login
    gcloud config set compute/zone europe-west2-b
    ```

    

    ## Scalable MongoDB configuration for kubernetes

15. The first step is to create the kubernetes cluster so we can start bulding the storage configuration for the MongoDB deployment. Back on the laptop, not the cffa-builder server. TO DO, reduce node VM boot disk to 10GB:

    ```bash
    gcloud container clusters create "cffa-cluster" --num-nodes=6 --machine-type e2-small
    ```

    If this fails with an error: 500 "Internal error encountered" this may be related to an issue with the service account. (https://cloud.google.com/kubernetes-engine/docs/troubleshooting#gcloud) For me this fixed it, and then rerunning the cluster create command:

    ```bash
    gcloud services enable container.googleapis.com
    ```

16. We need to create persistent data store for MongoDB. To improve resiliency the data is being replicated across two locations in the same zone. We define the storage class first before provisioning the storage

    ```shell
    cd $HOME
    vi gce-ssd-storageclass.yaml
    ```

    ```yaml
    kind: StorageClass
    apiVersion: storage.k8s.io/v1beta1
    metadata:
      name: fast
    provisioner: kubernetes.io/gce-pd
    parameters:
      type: pd-ssd
    ```

    ```bash
    kubectl apply -f gce-ssd-storageclass.yaml
    ```

17. When provisioning the storage we create 3 disks, one for each MongoDB instance that we plan to be running.

    ```bash
    gcloud compute disks create --size 10GB --type pd-ssd pd-ssd-disk-1 --replica-zones europe-west2-b,europe-west2-c
    gcloud compute disks create --size 10GB --type pd-ssd pd-ssd-disk-2 --replica-zones europe-west2-b,europe-west2-c
    gcloud compute disks create --size 10GB --type pd-ssd pd-ssd-disk-3 --replica-zones europe-west2-b,europe-west2-c
    ```

    and to configure  how the storage will be used:

    ```bash
    vi gce-ssd-persistentvolume1.yaml
    ```

    ```yaml
    apiVersion: "v1"
    kind: "PersistentVolume"
    metadata:
      name: data-volume-1
    spec:
      capacity:
        storage: 2Gi
      accessModes:
        - ReadWriteOnce
      persistentVolumeReclaimPolicy: Retain
      storageClassName: fast
      gcePersistentDisk:
        pdName: pd-ssd-disk-1
    ```

18. Repeat the persistent volumes for no2 and no3:

    ```yaml
    vi gce-ssd-persistentvolume2.yaml
    ```

    ```yml
    apiVersion: "v1"
    kind: "PersistentVolume"
    metadata:
      name: data-volume-2
    spec:
      capacity:
        storage: 2Gi
      accessModes:
        - ReadWriteOnce
      persistentVolumeReclaimPolicy: Retain
      storageClassName: fast
      gcePersistentDisk:
        pdName: pd-ssd-disk-2
    ```

    ```bash
    vi gce-ssd-persistentvolume3.yaml
    ```

    ```yaml
    apiVersion: "v1"
    kind: "PersistentVolume"
    metadata:
      name: data-volume-3
    spec:
      capacity:
        storage: 2Gi
      accessModes:
        - ReadWriteOnce
      persistentVolumeReclaimPolicy: Retain
      storageClassName: fast
      gcePersistentDisk:
        pdName: pd-ssd-disk-3
    ```

19. Apply the persistent volume definitions and confirm

    ```bash
    kubectl apply -f gce-ssd-persistentvolume1.yaml
    kubectl apply -f gce-ssd-persistentvolume2.yaml
    kubectl apply -f gce-ssd-persistentvolume3.yaml
    kubectl get persistentvolumes
    ```

20. Create a secret for MongoDB authentication - this secret will be available for each mongo DB server.:

    ```bash
    /usr/bin/openssl rand -base64 741 > mysecret
    kubectl create secret generic shared-bootstrap-data --from-file=mysecret
    rm mysecret
    ```

21. Now edit for Kubernetes yaml for the mongoDB scalable service:

    ```bash
    vi mongodb-service.yaml
    ```

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: mongodb-service
      labels:
        name: mongo
    spec:
      ports:
      - port: 27017
        targetPort: 27017
      clusterIP: None
      selector:
        role: mongo
    ---
    apiVersion: apps/v1beta1
    kind: StatefulSet
    metadata:
      name: mongod
    spec:
      serviceName: mongodb-service
      replicas: 3
      template:
        metadata:
          labels:
            role: mongo
            environment: test
            replicaset: MainRepSet
        spec:
          terminationGracePeriodSeconds: 10
          volumes:
            - name: secrets-volume
              secret:
                secretName: shared-bootstrap-data
                defaultMode: 256
          containers:
            - name: mongod-container
              image: mongo
              command:
                - "mongod"
                - "--bind_ip"
                - "0.0.0.0"
                - "--replSet"
                - "MainRepSet"
                - "--auth"
                - "--clusterAuthMode"
                - "keyFile"
                - "--keyFile"
                - "/etc/secrets-volume/mysecret"
                - "--setParameter"
                - "authenticationMechanisms=SCRAM-SHA-1"
              ports:
                - containerPort: 27017
              volumeMounts:
                - name: secrets-volume
                  readOnly: true
                  mountPath: /etc/secrets-volume
                - name: mongodb-persistent-storage-claim
                  mountPath: /data/db
      volumeClaimTemplates:
      - metadata:
          name: mongodb-persistent-storage-claim
          annotations:
            volume.beta.kubernetes.io/storage-class: "fast"
        spec:
          accessModes: [ "ReadWriteOnce" ]
          resources:
            requests:
              storage: 2Gi
    ```

22. Now we can start apply the configuration into kubernetes which will start MongoDB instances:

    ```bash
    kubectl apply -f mongodb-service.yaml
    ```

23. Track the deployment progress by running the following command repeatedly:

    ```bash
    kubectl get all
    ```

24. Set up MongoDB replication across the 3 instances and set the MongoDB admin user. This involves logging into the first container:

    ```bash
    kubectl exec -it mongod-0 -c mongod-container bash
    
    mongo
    
    rs.initiate({_id: "MainRepSet", version: 1, members: [
        { _id: 0, host : "mongod-0.mongodb-service.default.svc.cluster.local:27017" },
        { _id: 1, host : "mongod-1.mongodb-service.default.svc.cluster.local:27017" },
        { _id: 2, host : "mongod-2.mongodb-service.default.svc.cluster.local:27017" }
     ]});
    ```

25. Check the status of the replica set whilst in the Mongo command line:

    ```
    rs.status();
    ```

26. Now set the cffa admin account:

    ```
    db.getSiblingDB("admin").createUser({
          user : "footballdba",
          pwd  : "pearce1990",
          roles: [ { role: "root", db: "admin" } ]
     });
    ```

27. Now leave Mongo and log back in as this new dba user, then create the cffa db user for the app:

    ```
    exit
    ```

    ```bash
    mongo admin -u footballdba -p pearce1990
    ```

    ```
    use footballDB
    db.createUser( { user: "cffa", pwd: "robson1986", roles:  [ { role: "readWrite", db: "footballDB" } ] } );
    exit
    ```

    Test the URI string to confirm it is working (same string CFFA will use):

    ```bash
    mongo mongodb://cffa:robson1986@mongod-0.mongodb-service,mongod-1.mongodb-service,mongod-2.mongodb-service:27017/footballDB
    ```

    Output will be similar to this:

    ```
    connecting to: mongodb://mongod-0.mongodb-service:27017,mongod-1.mongodb-service:27017,mongod-2.mongodb-service:27017/footballDB?compressors=disabled&gssapiServiceName=mongodb
    Implicit session: session { "id" : UUID("xxxxxxxx-dd17-491b-bb06-7389c74b4da5") }
    MongoDB server version: 4.2.8
    ```

28.  Now exit the mongo session and then the container:

    ```
    exit
    exit
    ```

29. This is now complete with a Mongo DB running replicating amongst themselves.

    ### Build CFFA container ###

30. Back on the cffa-builder server:

    ```
    cd $HOME
    ```

31. Get the cffa and cffadb code from GitHub:

    ```
    git clone https://github.com/GreyPaperclip/cffa
    mkdir cffadb
    cd cffadb
    git clone https://github.com/GreyPaperclip/cffadb
    cd ..
    ```

32. Create the boot.sh file that is executed when the container starts:

    ```bash
    vi boot.sh
    ```

    ```bash
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
    ```

33. Create the Dockerfile to build container. Note the use of alpline lightweight version of python in this Tutorial compared to the Raspberry PI one:

    ```bash
    vi Dockerfile
    ```

    ```Dockerfile
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
    ```

34. Unlike the Raspberry PI tutorial, Docker is not required to build a container as Google provide tooling. The command below will remotely build the container on a storage bucket (on gcr.io/cffa/scalable). The first time this is run, you will be asked to enable the google api:

    ```bash
    gcloud builds --project cffa-scalable submit --tag gcr.io/cffa-scalable/cffa-app:v0.0.1
    ```

    Note: if the command files with the error "`lstat /workspace/Dockerfile: no such file or directory`" - make sure you are in the same directory as $HOME/cffa as the Dockerfile must be in the current working directory.

    Note 2: This command may fail due to a "`Caller does not have permission 'storage.buckets.get`'" error. This may require you to run `gsutil list`, to show the storage bucket and execute the following command:

    ```bash
    gsutil iam ch user:<your email address>:storageAdmin gs://<name of storage bucket>
    ```

35. Check the container was built successfully by checking the STATUS:

    ```bash
    gcloud builds --project cffa-scalable list
    ```

    Example output:

    ```
    ID                                    CREATE_TIME                DURATION  SOURCE                                                                                       IMAGES                                STATUS
    xxxxxxxx-7a7b-4b12-abd0-f1b102f8ef09  2020-07-19T19:50:02+00:00  2M28S     gs://cffa-scalable_cloudbuild/source/1595188200.966285-746e8828a16c40a29ce78xxxxxxxx.tgz  gcr.io/cffa-scalable/cffa-app:v0.0.1  SUCCESS
    ```

36. Make the self-signed certificates for cffa:

    ```bash
    mkdir $HOME/certs
    cd $HOME/certs
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:4096 -keyout ./cffa-selfsigned.key -out ./cffa-selfsigned.crt
    cd $HOME/cffa
    ```

37. Create the cffa yaml file for kubernetes to deploy CFFA onto the cluster

    ```bash
    vi cffa.yaml
    ```

    ```yaml
    apiVersion: apps/v1beta2
    kind: Deployment
    metadata:
      name: cffa-flask-app
      labels:
        name: cffa-flask-app
    spec:
      replicas: 1
      selector:
        matchLabels:
          name: cffa-flask-app
      template:
        metadata:
          name: cffa-flask-app
          labels:
            name: cffa-flask-app
        spec:
          volumes:
            - name: pd-ssd-website-cffa
              persistentVolumeClaim:
                claimName: pd-ssd-website-storage
                readOnly: true
          containers:
            - name: cffa-flask-app
              image: gcr.io/cffa-scalable/cffa-app:v0.0.1
              ports:
                - containerPort: 5000
              resources:
                requests:
                  memory: 256Mi
                limits:
                  memory: 512Mi
              volumeMounts:
                - name: pd-ssd-website-cffa
                  mountPath: /home/cffa/shared
                  readOnly: true
              env:
                - name: SECRET_KEY
                  value: "any secret key"
                - name: AUTH0_CLIENT_ID
                  value: "Your AUth0 Client ID for your app"
                - name: AUTH0_DOMAIN
                  value: "Your Auth0 Domain"
                - name: AUTH0_CLIENT_SECRET
                  value: "Your Auth0 Client Secret"
                - name: AUTH0_CALLBACK_URL
                  value: "https://cffa.yourdomain.com/callback"
                - name: BACKEND_DBPWD
                  value: "pearce1990"
                - name: BACKEND_DBUSR
                  value: "footballdba"
                - name: BACKEND_DBHOST
                  value: "mongod-0.mongodb-service,mongod-1.mongodb-service,mongod-2.mongodb-service"
                - name: BACKEND_DBPORT
                  value: "27017"
                - name: BACKEND_DBNAME
                  value: "footballDB"
                - name: EXPORTDIRECTORY
                  value: "/home/cffa/ExportImport"
    ```

    

38. The yaml refers to persistent storage - as CFFA could be running across a number of kubernetes nodes, we will configure it so each node will be accessing the same static, templates directories and certificate files. By sharing these data we can also update any files and certificates without having to rebuild the container (which copies other files such as the source code) . This makes the container more portable.

    ```bash
    gcloud compute disks create --size 10GB --type pd-ssd pd-ssd-cffawebsite --replica-zones europe-west2-b,europe-west2-c
    ```

39. Execute lsblk to check current disks attached to the instance. We will use this to determine to which drive the above disk can be identified: 

    ```bash
    sudo lsblk
    ```

    Example output:

    ```
    NAME   MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
    sda      8:0    0   20G  0 disk 
    ├─sda1   8:1    0  200M  0 part /boot/efi
    └─sda2   8:2    0 19.8G  0 part /
    sdb      8:16   0   16G  0 disk 
    ```

40. Attach the storage to our server:

    ```bash
    gcloud compute instances attach-disk cffa-builder --zone europe-west2-b --disk pd-ssd-cffawebsite --disk-scope regional
    ```

41. Execute lsblk again to see the new disk. This may be shown as /dev/sdb or /dev/sdc

    ```bash
    sudo lsblk
    ```

    Example output. In this case we can seen **sdc** has just been added:

    ```
    NAME   MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
    sda      8:0    0   20G  0 disk 
    ├─sda1   8:1    0  200M  0 part /boot/efi
    └─sda2   8:2    0 19.8G  0 part /
    sdb      8:16   0   16G  0 disk 
    sdc      8:32   0   10G  0 disk 
    ```

42. Now format the disk changing the last drive ID as required.

    ```bash
    sudo mkfs.ext4 -m 0 -E lazy_itable_init=0,lazy_journal_init=0,discard /dev/sdc
    ```

43. And mount the formatted drive:

    ```bash
    mkdir shared
    sudo mount -o discard,defaults /dev/sdc ./shared
    ```

44. Copy across the certs, the template directory, and then the static directory

    ```bash
    cd $HOME/cffa
    sudo mkdir -p shared/certs shared/templates shared/static
    sudo cp ../certs/* shared/certs/.
    sudo cp templates/* shared/templates/.
    sudo cp templates/* shared/templates/.
    sudo chmod a+r -R shared
    ```

45. Unmount the drive and remove ssd from server.

    ```bash
    sudo umount /dev/sdc
    gcloud compute instances detach-disk cffa-builder --disk pd-ssd-cffawebsite --disk-scope regional --zone europe-west2-b
    ```

46. Now in $HOME, define the how the storage will be mounted on the kubernetes nodes

    ```bash
    cd $HOME
    vi gce-ssd-cffawebsite.yaml
    ```

    ```yaml
    apiVersion: v1
    kind: PersistentVolume
    metadata:
      name: pv-shared
    spec:
      storageClassName: "example-storageclass"
      capacity:
        storage: 10G
      accessModes:
        - ReadOnlyMany
      claimRef:
        namespace: default
        name: pd-ssd-website-storage
      gcePersistentDisk:
        pdName: pd-ssd-cffawebsite
        fsType: ext4
    ---
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: pd-ssd-website-storage
    spec:
      storageClassName: "example-storageclass"
      accessModes:
        - ReadOnlyMany
      resources:
        requests:
          storage: 10G
    ```

47. Set up the persistent volume definition in kubernetes:

    ```bash
    kubectl apply -f gce-ssd-cffawebsite.yaml
    ```

    ```bash
    persistentvolume/pv-shared created
    persistentvolumeclaim/pd-ssd-website-storage created
    ```

48. We are now in a position to start the cffa app:

    ```bash
    cd $HOME/cffa
    kubectl apply -f cffa.yaml
    ```

49. Run get pods several times to see the container start up

    ```bash
    kubectl get pods
    ```

    ```
    NAME                              READY   STATUS              RESTARTS   AGE
    cffa-flask-app-6ccd7f86bf-kmqsl   0/1     ContainerCreating   0          50s
    mongod-0                          1/1     Running             0          47h
    mongod-1                          1/1     Running             0          70m
    mongod-2                          1/1     Running             0          70m
    ```

    Note: if the pod stays in ContainerCreating troubleshooting is required. Execute (change the cffa-flask-app name to your one):

    ```bash
    kubectl describe pod cffa-flask-app-6ccd7f86bf-kmqsl
    ```

    and review the output. For example, an error 

    ```
      Warning  FailedAttachVolume  80s (x9 over 4m5s)  attachdetach-controller                          AttachVolume.Attach failed for volume "pv-shared" : googleapi: Error 400: RESOURCE_IN_USE_BY_ANOTHER_RESOURCE - The disk resource 'projects/cffa-scalable/regions/europe-west2/disks/pd-ssd-cffawebsite' is already being used by 'projects/cffa-scalable/zones/europe-west2-b/instances/cffa-builder'
    ```

    indicates the drive wasn't unmounted/detached from cffa-builder first. Resolve this issue and then delete the pod by running (kubernetes will start a new one)

    ```bash
    kubectl delete pod cffa-flask-app-6ccd7f86bf-kmqsl
    ```

    Other potential errors might be  "`/home/cffa/shared/certs/cffa-selfsigned.crt`"  which could mean a problem mounting the pd-ssd-website-storage persistent volume. 

50. Check the cffa logs, a good running container should show similar logs:

    ```bash
    kubectl logs cffa-flask-app-5dcf99c67-w4xll
    ```

    ```
    [2020-07-19 20:51:45 +0000] [1] [INFO] Starting gunicorn 20.0.4
    [2020-07-19 20:51:45 +0000] [1] [DEBUG] Arbiter booted
    [2020-07-19 20:51:45 +0000] [1] [INFO] Listening at: https://0.0.0.0:5000 (1)
    [2020-07-19 20:51:45 +0000] [1] [INFO] Using worker: sync
    [2020-07-19 20:51:45 +0000] [18] [INFO] Booting worker with pid: 18
    [2020-07-19 20:51:45 +0000] [1] [DEBUG] 1 workers
    ```

    ### Load balancer configuration and Ingress configuration ###

51. Now CFFA and MongoDB are running, we now need to expose the webserver to the Internet. To do this we need to define a load balance for https and an ingress point let the traffic come in.

52. Create self-signed certificates for the load balancer secrets. Update the line for your domain:

    ```bash
    cd $HOME/certs
    openssl genrsa -out cffa-ingress.key 2048
    openssl req -new -key cffa-ingress.key -out cffa-ingress.csr -subj "/CN=cffa.yourdomain.com"
    openssl x509 -req -days 365 -in cffa-ingress.csr -signkey cffa-ingress.key -out cffa-ingress.crt
    kubectl create secret tls cffa-secret --cert cffa-ingress.crt --key cffa-ingress.key
    ```

53. Define the load balancer configuration:

    ```bash
    cd $HOME
    vi service_https_loadbalancer.yaml
    ```

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: ingress-service-cffa
      annotations:
        cloud.google.com/app-protocols: '{"my-https-port":"HTTPS"}'
    spec:
      type: NodePort
      selector:
        name: cffa-flask-app
      ports:
      - name: my-https-port
        port: 443
        targetPort: 5000
    ```

    and apply it:

    ```bash
    kubectl apply -f service_https_loadbalancer.yaml
    ```

    Output will be:

    ```
    service/ingress-service-cffa created
    ```

54. Now define the ingress. Note that you will need to update the host value to your domain

    ```bash
    vi ingress.yaml
    ```

    ```yaml
    apiVersion: networking.k8s.io/v1beta1
    kind: Ingress
    metadata:
      name: cffa-ingress
    spec:
      tls:
      - secretName: cffa-secret 
      rules:
      - host: cffa.yourdomain.com
        http:
          paths:
          - path: /*
            backend:
              serviceName: ingress-service-cffa
              servicePort: 443
    ```

    and apply it:

    ```bash
    kubectl apply -f ingress.yaml
    ```

55. It may take up to 15 minutes to create the load balancer  in the background. Once created an IP will be allocated to it (under Status). This can be viewed by running the command:

    ```bash
    kubectl get ingress cffa-ingress --output yaml
    ```

    ```
    ...
    spec:
      rules:
      - host: cffa2.richardborrett.com
        http:
          paths:
          - backend:
              serviceName: ingress-service-cffa
              servicePort: 443
            path: /*
      tls:
      - secretName: cffa-secret
    status:
      loadBalancer:
        ingress:
        - ip: 34.xxx.xxx.xxx
    ```

    

56. In your web browser, go to https://34.xxx.xxx.xxx. This should show a untrusted connection (your self-signed keys). Click on show details to confirm this.

    ![Self signed certficate](https://lh3.googleusercontent.com/pw/ACtC-3d4QHSCLt-Hl1Q1C5U_NajAm6600ZBrR5ay437DeVAWFtcWdfFoY2Xo5npuWHxvVqXV3-huwOd7HIU9p4dHDp4aYqnvcjswd0lscFD6VyswR2TPlVyZMl9YKbRiaE9ye7arRrR1YtrODNrAw82O1OEr=w704-h478-no)

57. Now log into your DNS provider, and update your cffa.yourdomain.com A record to direct to the load balancer IP address.

58. Go back to your web browser and log into cffa.yourdomain.com. You should now be prompted with the login page:

    ![CFFA login endpoint](https://lh3.googleusercontent.com/pw/ACtC-3fSmp7A7M_0S6odC5mbar6u38Bvph12KuaC0VOH5RF67CmTgrpFLWrw2oQJdoZVEPObHSd3xTBkWOXgE1wFTzErnGTX8ch_5Jv_XN0tc0zG3B4dJknGHTmnMThXnR2GVspjQQaklp9N0pKJc6JX3Kef=w1043-h560-no)

59. Login should work if you have a user created in Auth0 and you'll be prompted to add a new team name.

60. If errors occur you can use the following to help troubleshoot:

    Get summary of pod status:

    ```bash
    kubectl get pods
    ```

    Describe the pod in more detail:

    ```bash
    kubectl describe pod **pod-name**
    ```

    Get logs of a pod

    ```bash
    kubectl logs **pod-name**
    ```

    Connect to the pod to troubleshoot on the command line (if it is running):

    ```bash
    kubectl exec -it **containerInstance**-0 -c **containerName** bash
    ```

### Scaling up and Down ###

At a basic level, Kubernetes allows you to easily scale out the CFFA service using the following command:

kubectl scale deployment cffa-flask-app --replicas=X

where X is the number of flask webservers. Note that more than 1 cffa-flask-app can run at the same time on the same kubernetes notes, so with a 5 node kubernetes clusters, it is possible to run 10 cffa-flask-apps.

The load balancer will route any browser request to any of the flask webservers. If you are implementing a flask app, there is  a consideration as you cannot assume that a user always enters the app through the login page. In CFFA's case, there is [TO DO: will be shortly!] a decorator for each endpoint that ensures the user tenancy is set (otherwise the user is bounced to the onboarding page). If this logic is not implemented you will see a similar message when a web browser is directed to any other flask server that did not handle the login on the entryScreen endpoint.

```python
{
  "message": "'FootballDB' object has no attribute 'games'"
}
```

#### Auto-scaling ####

Kubernetes allows auto-scaling based on resource thresholds. This is out of scope for this Tutorial but would be a useful topic for later coverage.

#### MongoDB scaling #### 

The MongoDB deployment in this tutorial consists of 1 primary MongoDB with replication to the other two MongoDB instances. This is a fixed configuration as it is explicitly defined in step 24. It is possible to use the same scaling command for mongod, but no difference should be observed from a CFFA point of view, as CFFA is explictly told to use only the first three mongo servers for the database. It is out of scope of this tutorial to cover MongoDB [auto]scaling but there will be Internet resources to cover various use cases

### Shutdown and Teardown

Instead of deleting the kubernetes cluster, you may wish to shutdown the cluster without deletion if you wish to start the system up again. Note that some costs will continue to be incurred as Google will still be storing all the data on the SSD partitions and the load balanc. However no compute cost will be incurred.

### Shutdown Steps ###

1. Reduce the mongoDB replica sets to 0, then cffa, then the  kubernetes cluster to 0 nodes. 

   ```bash
   kubectl scale --replicas=0 statefulset mongod
   kubectl scale deployment cffa-flask-app --replicas=0
   kubectl get pods
   gcloud container clusters resize cffa-cluster --num-nodes=0 --zone=europe-west2-c
   ```

2. To reduce cost you may wish to remove the load balancer:

   ```bash
   kubectl delete service ingress-service-cffa
   kubectl delete ingress cffa-ingress
   ```

3. On the cffa-builder service

   ```
   sudo shutdown
   ```

4. Then, after 60 seconds on your laptop, run:

   ```bash
   gcloud compute instances stop cffa-builder
   ```

### Startup Steps after previous shutdown without cffa-builder. ###

1. It is possible to run kubectl commands via gcloud on your laptop. This means you don't need to keep (and incur cost) of cffa-builder server

   ```bash
   gcloud components install kubectl
   ```

   Make sure you are using your google account and set the project to cffa-scalable and the preferred zone:

   ```bash
   gcloud init
   gcloud container clusters get-credentials cffa-cluster
   ```

2. On your laptop copy across the ingress.yaml and service_https_loadbalancer.yaml files (or paste from this tutorial) and execute the two kubectl commands to set up the load balancer:

   ```bash
   kubectl apply -f service_https_loadbalancer.yaml
   kubectl apply -f ingress.yaml
   ```

3. Now check the IP address as it may be different now (NB: TO DO: check why it isn't in my case). If it has changed update your DNS A record entry:

   ```bash
   kubectl get ingress cffa-ingress --output yaml
   ```

4. Now scale the cluster back up to start up the MongoDB and CFFA nodes:

   ```bash
   gcloud container clusters resize cffa-cluster --size=4 --zone=europe-west2-c
   kubectl scale --replicas=3 statefulset mongod
   kubectl scale deployment cffa-flask-app --replicas=1
   ```

5. Go to your web browser and log into CFFA! Note: you may need to wait up to 15 minutes for the load balancer to provision.

6. If you wanted to start of cffa-builder again and log in, execute:

   ```bash
   gcloud compute instances start-cffabuilder
   gcloud compute ssh --project cffa-scalable --zone europe-west2-b cffa-builder
   ```

### Tear Down of all resources ###

1. Logged onto cffa-scalable: remove the load balancer and cluster (cluster deletion will remove the balancer but being explicit here):

   ```bash
   kubectl delete service ingress-service-cffa
   kubectl delete ingress cffa-ingress
   gcloud container clusters delete cffa-cluster
   ```

2. Now list and then remove your CFFA container image:

   ```bash
   gcloud container images list
   ```

   For each tag (should only be one), execute:

   ```bash
   gcloud container images list-tags gcr.io/cffa-scalable/cffa-app
   gcloud container images delete gcr.io/cffa-scalable/cffa-app:v0.0.1
   ```

3. Now remove the storage for MongoDB instances:

   ```bash
   gcloud compute disks list
   gcloud compute disks delete pd-ssd-disk-1 --region europe-west2
   gcloud compute disks delete pd-ssd-disk-2 --region europe-west2
   gcloud compute disks delete pd-ssd-disk-3 --region europe-west2
   ```

4. And now remove the shared storaged for CFFA flask instances:

   ```bash
   gcloud compute disks delete pd-ssd-website --region europe-west2
   ```

5. Now remove cffa-builder. Shutdown and logout

   ```shell
   sudo shutdown
   # Press enter
   exit
   ```

6. Stop and then delete server:

   ```shell
   gcloud compute instances stop cffa-builder --project cffa-scalable --zone europe-west2-c
   gcloud compute instances delete cffa-builder --project cffa-scalable --zone europe-west2-c
   ```

7. Now delete the project (note this will remove any remaining storage bucket data):

   ```shell
   gcloud projects list
   gcloud projects delete cffa-scalable
   gcloud projects list
   ```

8. You may wish to log back into console.cloud.google.com to confirm all has been removed.

