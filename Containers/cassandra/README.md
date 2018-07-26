# Cassandra

These are the containers used in the cassandra experiment

There are the server and the setup-server

## Setup-Server

This will create the correct databases used by YCSB

## Server

This will run the Cassandra nodes



# Makefile
There are 3 commands

- build-server: builds the server
- build-setup-server: builds the setup server
- push: Pushes changes to the Docker Hub


# Set up

In the makefile, change the `$$USER` variable to your username in Docker Hub Repo
