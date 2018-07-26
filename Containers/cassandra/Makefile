USER=mapa12
REPO=cassandra
TAG_normal=server
TAG_setup=setup

all: push

build-server: Dockerfile_cassandra_server mapa12-entrypoint.sh
	echo -e "\e[31mBuilding ${USER}/${REPO}:${TAG_normal} \e[0m"
	docker build -t ${USER}/${REPO}:${TAG_normal} -f Dockerfile_cassandra_server .

build-setup-server: Dockerfile_cassandra_setup_db setup_database.cql setup_database.sh
	echo -e "\e[31mBuilding ${USER}/${REPO}:${TAG_setup} \e[0m"
	docker build -t ${USER}/${REPO}:${TAG_setup} -f Dockerfile_cassandra_setup_db .

push: build-server build-setup-server
	echo -e "\e[31mPush ${USER}/${REPO} \e[0m"
	docker push ${USER}/${REPO}
