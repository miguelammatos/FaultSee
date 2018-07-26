---
layout: default
---

# Angainor

Reproducing experimental results is a core tenet of the scientific method.
Unfortunately, the increasing complexity of the system we build, deploy and evaluate makes it difficult to reproduce results and hence is one of the greatest impairments for the progress of science in general and distributed systems in particular.

The complexity stems not only from the increasing complexity of the systems under study, but also from the inherent complexity of capturing and controlling all variables that can potentially affect experimental results.

We argue that this can only be addressed with a systematic approach to all the stages of the evaluation process.
Angainor is a step in this direction.

Our goal is to address the following challenges: i) precisely describe the environment and variables affecting the experiment, ii) minimize the number of (uncontrollable) variables affecting the experiment and iii) have the ability to subject the system under evaluation to controlled fault patterns.



# How to use


## Requirements
* Docker >= 1.12
* OpenJDK or OracleJDK >= 8
* Python >= 3.5
* pip >= 9.0.1
* GNU bash

### Locally
1. Have a Docker client/daemon up and running on your machine. Check the [Docker documentation](https://docs.docker.com/install/) for instructions.

2. Build the Docker images and push them to a local registry
```bash
make all && make push
```

3. Enable lsdsuite ipam-plugin
```bash
docker plugin enable 127.0.0.1:5000/lsdsuite/lsdsuite-ipam:latest
```

4. Check `config.yaml` and adjust it accordingly to your system. The provide defaults provided should work in most cases.

5. Initialize a _cluster_ with only the local node.
```bash
bash bin/lsds cluster init
```

6. Start the cluster
```bash
bash ./bin/lsds cluster up
```

7. Check the status of the _cluster_ with
```bash
./bin/lsds cluster status
```

8. Let's run a simple deployment with a nginx server and a siege client.
```bash
./bin/lsds benchmark --app examples/nginx/nginx.yaml --name hello-world --run-time 120
```
which will run the experiment for 120 seconds.

9. To run a more interesting scenario with churn
```bash
./bin/lsds benchmark --app examples/nginx/nginx.yaml --name newng --churn examples/nginx/churn.yaml
```

10. Results will become available at `<date>-<experiment-name>`

11. To shutdown the _cluster_ run
```bash
./bin/lsds cluster down
```

### In a cluster
1. Have a cluster ready with Docker running on every host and make sure that every host is accessible though ssh.
2. Adjust `config.yaml` to match your cluster settings, with one entry per each cluster machine
3. To run an experiment in the cluster follow steps 4-9 of the local deployment.


# Contribute

If you find any issue or would like to contribute with new features open a new issue and we will get in touch as soon as possible.

## Funding

This work was partially supported by Fundo Europeu de Desenvolvimento Regional (FEDER) through Programa Operacional Regional de Lisboa and by Fundação para a Ciência e Tecnologia (FCT) through projects with reference UID/CEC/50021/2013 and LISBOA-01-0145-FEDER-031456.
