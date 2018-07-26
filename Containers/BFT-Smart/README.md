# BFT-Smart

This is the container used in the BFT-Smart experiment

The Folder `code` is a copy of the repository : at commit (8 Aug 2019)

The files are not original:
- code/config/hosts.config - changed to experiment hosts
- code/config/custom_java_security_file - File created to replace the java.security file in order for the experiment to run smoothly.

The YCSB runscripts were also changed


## Server

This will run the BFT-Smart nodes

# Makefile
There are 2 commands

- build: builds the BFT-Smart server
- push: Pushes changes to the Docker Hub

# Set up

In the makefile, change the `$$USER` variable to your username in Docker Hub Repo
