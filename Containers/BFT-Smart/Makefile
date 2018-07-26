USER=mapa12
REPO=bft-smart-experiment
TAG=latest

all: push

build:
	docker build -t ${USER}/${REPO}:${TAG} .
	echo -e "\e[31mBuilding ${USER}/${REPO}:${TAG} \e[0m"
	docker build -t ${USER}/${REPO}:${TAG} -f Dockerfile .

push: build
	echo -e "\e[31mPush ${USER}/${REPO} \e[0m"
	docker push ${USER}/${REPO}
