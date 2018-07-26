USER=mapa12
LSDSUITE_IPAM_PLUGIN_NAME=lsdsuite-ipam

all: clean build create push

clean:
	docker rm -vf plugin-tmp || true
	rm -rf ./plugin

build:
	docker build -t ${USER}/${LSDSUITE_IPAM_PLUGIN_NAME}:rootfs .
	mkdir -p ./plugin/rootfs
	docker create --name plugin-tmp ${USER}/${LSDSUITE_IPAM_PLUGIN_NAME}:rootfs
	docker export plugin-tmp | tar -x -C ./plugin/rootfs app
	cp config.json ./plugin/
	docker rm -vf plugin-tmp

create:
	docker plugin rm -f ${USER}/${LSDSUITE_IPAM_PLUGIN_NAME} || true
	docker plugin create ${USER}/${LSDSUITE_IPAM_PLUGIN_NAME} ./plugin

push:
	docker plugin push ${USER}/${LSDSUITE_IPAM_PLUGIN_NAME}
