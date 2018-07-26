USER=mapa12
REPO_NAME=ntp-sync
TAG=1.0

all: build push

build:
	echo -e "\e[31;1mIMAGE: ${USER}/${REPO_NAME}:${TAG} \e[0m"
	docker build -t ${USER}/${REPO_NAME}:${TAG} .

push:
	echo -e "\e[31;1mIMAGE: ${USER}/${REPO_NAME}:${TAG} \e[0m"
	docker push ${USER}/${REPO_NAME}:${TAG}
