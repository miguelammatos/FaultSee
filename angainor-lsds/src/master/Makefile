USER=mapa12
LSDSUITE_MASTER_NAME=faultsee-master

all: build push


build:
	./one_version_up.sh
	set -e ;\
	version=$$(./print_version.sh) ;\
	echo -e "\e[33;1mIMAGE: ${USER}/${LSDSUITE_MASTER_NAME}:$${version} \e[0m" ;\
	docker build -t ${USER}/${LSDSUITE_MASTER_NAME}:$${version} .
	docker build -t ${USER}/${LSDSUITE_MASTER_NAME}:dev_latest .

push:
	set -e ;\
	version=$$(./print_version.sh) ;\
	echo -e "\e[33;1mIMAGE: ${USER}/${LSDSUITE_MASTER_NAME}:$${version} \e[0m" ;\
	docker push ${USER}/${LSDSUITE_MASTER_NAME}:$${version}
	docker push ${USER}/${LSDSUITE_MASTER_NAME}:dev_latest
