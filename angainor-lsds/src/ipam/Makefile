USER=mapa12
LSDSUITE_IPAM_PLUGIN_NAME=faultsee-ipam
LSDSUITE_IPAM_SERVER_NAME=ipam-server

all:
	echo -e "\e[31;1mUSER: ${USER} \e[0m"
	cd plugin; make USER=${USER} LSDSUITE_IPAM_PLUGIN_NAME=${LSDSUITE_IPAM_PLUGIN_NAME}
	cd server; make USER=${USER} LSDSUITE_IPAM_SERVER_NAME=${LSDSUITE_IPAM_SERVER_NAME}

push:
	echo -e "\e[31;1mUSER: ${USER} \e[0m"
	cd plugin; make push USER=${USER} LSDSUITE_IPAM_PLUGIN_NAME=${LSDSUITE_IPAM_PLUGIN_NAME}
	cd server; make push USER=${USER} LSDSUITE_IPAM_SERVER_NAME=${LSDSUITE_IPAM_SERVER_NAME}
