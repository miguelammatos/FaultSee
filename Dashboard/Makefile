USERNAME=mapa12/
IMAGE-NAME=plot-webserver

all: build run

build: src
	./one_version_up.sh
	set -e ;\
	version=$$(./print_version.sh) ;\
	echo -e "\e[33mBUILD: ${USERNAME}${IMAGE-NAME}:$${version} \e[0m" ;\
	docker build -t ${USERNAME}${IMAGE-NAME}:$${version} . ;\
	docker build -t ${USERNAME}${IMAGE-NAME}:dev_latest .

run: 
	set -e ;\
	version=$$(./print_version.sh) ;\
	echo -e "\e[33;1mRUN: ${USERNAME}${IMAGE-NAME}:$${version} \e[0m" ;\
	docker run --rm -p 8081:3000 --name faultsee-dash -v $$(pwd)/src:/usr/src/app/src ${USERNAME}${IMAGE-NAME}:dev_latest

push:
	set -e ;\
	version=$$(./print_version.sh) ;\
	echo -e "\e[33;1mPUSH: ${USERNAME}${IMAGE-NAME}:$${version} \e[0m" ;\
	docker push ${USERNAME}${IMAGE-NAME}:dev_latest ;\
	docker push ${USERNAME}${IMAGE-NAME}:$${version}
 
