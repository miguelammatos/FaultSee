# QuickStart

# FaultSee

FaultSee is a fault injection tool to easily test how distributed systems react in case of components failures

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

What things you need to install the software and how to install them

```
Docker
Make
Git
```

### Installing

A step by step series of examples that tell you how to get a development env running

# Install Git

```
sudo apt-get install -y git
```
# Install Make

```
sudo apt install -y make      
```

# Install Docker
Follow guidelines in https://docs.docker.com/install/linux/docker-ce/ubuntu/ to install docker stable version

```
sudo apt-get update

sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common
```
add repository key
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

add current user as a user who can manipulate docker containers

```
sudo groupadd docker

sudo usermod -aG docker $(whoami)
```
to add user a reboot is required

```
sudo reboot
```

## Run Simple Example

Compile code

```
cd angainor-lsds/src

# Edit Makefile Set $$USER variable to your Docker Hub username

make
```
### Change default configurations
$PROJECT_ROOT/angainor-lsds/bin/lsds is the script that helps to execute experiments

Change DOCKER_USER to your username

```
export DOCKER_USER=${DOCKER_USER:-"mapa12"}
```

### Cluster configuration
Create `$PROJECT_ROOT/angainor-lsds/config.yaml` to configure cluster

You can check `$PROJECT_ROOT/angainor-lsds/config.yaml.sample` for a detailed example

__NOTE: you need to have ssh access to all nodes (including master)__

The folder `$PROJECT_ROOT/angainor-lsds/keys` will be mounted in `/opt/lsdsuite/keys/`.
You can store SSH KEYS there if required.
```
cd $PROJECT_ROOT/angainor-lsds/

bash ./bin/lsds cluster up
```

### Start a simple experiment
```
cd $PROJECT_ROOT/angainor-lsds/

bash ./bin/lsds benchmark --app examples/nginx/docker-compose.yml --name hello-faultsee --churn examples/nginx/events.yml
```

## Dashboard

After Running the hello-faultsee experiment follow this [README](Dashboard/README.md) to see the results in the dashboard

---

# Deployment on multiple nodes

1. Have a cluster ready with Docker running on every host and make sure that every host is accessible though ssh.
2. Adjust config.yaml to match your cluster settings, with one entry per each cluster machine
3. Start the cluster
4. Start the experiment

# The FDSL specification is present at
[FDSL](./angainor-lsds/fdsl/README.md)

# A FDSL example with all options is available at    
[Full Example](./angainor-lsds/fdsl/experiment.yml)


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
