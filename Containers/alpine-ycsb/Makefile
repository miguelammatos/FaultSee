USER=mapa12
REPO=ycsb
TAG_normal=latest

all: push

build: Dockerfile start.sh
	echo -e "\e[31mBuilding ${USER}/${REPO}:${TAG_normal} \e[0m"
	docker build -t ${USER}/${REPO}:${TAG_normal} -f Dockerfile .

push: build
	echo -e "\e[31mPush ${USER}/${REPO} \e[0m"
	docker push ${USER}/${REPO}
