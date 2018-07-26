USER=mapa12/
LSDSUITE_IPAM_SERVER_NAME=ipam-server

all: build push

build:
	docker build -t ${USER}/${LSDSUITE_IPAM_SERVER_NAME} .

push:
	docker push ${USER}/${LSDSUITE_IPAM_SERVER_NAME}
