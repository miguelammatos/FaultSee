USER=mapa12
LSDSUITE_SLAVE_NAME=faultsee-slave

all: build push

build:
	./one_version_up.sh
	set -e ;\
	version=$$(./print_version.sh) ;\
	echo $${version} ;\
	echo -e "\e[31;1mIMAGE: ${USER}/${LSDSUITE_SLAVE_NAME}:$${version} \e[0m" ;\
	docker build -t ${USER}/${LSDSUITE_SLAVE_NAME}:$${version} .
	docker build -t ${USER}/${LSDSUITE_SLAVE_NAME}:dev_latest .

push:
	version=$$(./print_version.sh) ;\
	echo $${version} ;\
	echo -e "\e[31;1mIMAGE: ${USER}/${LSDSUITE_SLAVE_NAME}:$${version} \e[0m" ;\
	docker push ${USER}/${LSDSUITE_SLAVE_NAME}:$${version}
	docker push ${USER}/${LSDSUITE_SLAVE_NAME}:dev_latest
