# Start With Ubuntu Server 18.04 LTS

Follow guidelines in https://docs.docker.com/install/linux/docker-ce/ubuntu/ to install stable version

```
sudo apt-get update

sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common
```
# add repository key
```
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
```
```
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io
```
# add current user as a user who can manipulate docker containers
```
sudo groupadd docker

sudo usermod -aG docker $(whoami)
```
# to add user a reboot is required
```
sudo reboot
```
# if required install git
```
sudo apt-get install git
```
# download version from github
```
git clone https://github.com/miguelammatos/lsdsuite.git
```
# configuration

Create `$PROJECT_ROOT/angainor-lsds/config.yaml` to configure cluster

You can check `$PROJECT_ROOT/angainor-lsds/config.yaml.sample` for a detailed example

__NOTE: you need to have ssh access to all nodes (including master)__

The folder `$PROJECT_ROOT/angainor-lsds/keys` will be mounted in `/opt/lsdsuite/keys/`.
You can store SSH KEYS there if required.

# Start Cluster
```
bash $PROJECT_ROOT/angainor-lsds/bin/lsds cluster up
```

# Run example experiment
```
bash $PROJECT_ROOT/angainor-lsds/bin/lsds benchmark --app examples/nginx/docker-compose.yml --name hello-faultsee --churn examples/nginx/events.yml
```

## Dashboard

After Running the hello-faultsee experiment follow this [README](Dashboard/README.md) to see the results in the dashboard

---
# The FDSL specification is present at
[FDSL](./angainor-lsds/fdsl/README.md)

# A FDSL example with all options is available at    
[Full Example](./angainor-lsds/fdsl/experiment.yml)
