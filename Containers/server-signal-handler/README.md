# Server Signal handler

It is a simple web server that handles signals

It answers http requests on port 3000 and it closes on SIGINT / SIGTERM

On `make build` it creates a new docker image.

On `make push` it pushes the images to the Docker Hub Repo

On `make run` it launches a container locally

On `make signals ` it sends signals to the container running locally


# Set up

In the makefile, change the `$$USER` variable to your username in Docker Hub Repo
