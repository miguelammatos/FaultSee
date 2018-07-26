# Docker Swarm Visualizer

Helpful to see where containers are running

It must run on the master node of the experiment

For more information https://github.com/dockersamples/docker-swarm-visualizer

# Run

It can be started in two different ways:

```docker-compose up```

```$ docker run -it -d -p 8080:8080 -v /var/run/docker.sock:/var/run/docker.sock dockersamples/visualizer```
