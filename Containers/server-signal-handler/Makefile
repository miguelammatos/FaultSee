USER=mapa12
REPO=server-signal-handler

build:
	docker build -t ${USER}/${REPO}:latest .
	docker push ${USER}/${REPO}:latest

push:
	docker push ${USER}${IMAGE-NAME}:latest


# launches a container locally
run:
	USER=${USER} REPO=${REPO} bash run.sh

# sends signals to the container running locally
signals:
	bash sig-usr1.sh
	bash sig-term.sh
