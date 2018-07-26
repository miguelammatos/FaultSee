FROM ubuntu:16.04

RUN apt-get update
# RUN apt-get -y install vim

RUN apt-get -y install openjdk-8-jdk
RUN apt-get -y install ant

# solve code problems that prevented code from running smoothly
COPY code/config/custom_java_security_file /usr/lib/jvm/java-8-openjdk-amd64/jre/lib/security/java.security

RUN mkdir /source-code
WORKDIR /source-code


COPY code/doc doc
COPY code/lib lib

ENV HEAP_NEWSIZE 128M
ENV MAX_HEAP_SIZE 1024M

COPY code/src src
COPY code/build.xml .

# compile requirement
RUN mkdir bin

# compie
RUN ant

COPY code/runscripts runscripts
COPY code/config config
