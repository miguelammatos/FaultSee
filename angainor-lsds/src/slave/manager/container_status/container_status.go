package container_status

import (
	"fmt"
	"sync"
)


// ContainersStatus strucutre that holds information if container is alive or not
// First Map
//     key is service_name
//     value is map containing steps of all containers of service
//              second map
//              key is container slot number (inside service)
//              value is containerId. If key exists, then container is alive
type ContainersStatus struct {
	// maps are not thread safe, so we use RWMutex to protect it
	sync.RWMutex

	data map[string](map[int](string))
}

func CreateEmptyContainerStatus() ContainersStatus{
	return ContainersStatus{
		data:			make(map[string]map[int]string),
	}
}

func (containersStatus ContainersStatus) ContainerPresent(serviceName string, serviceSlot int) (string, bool) {
	containersStatus.RLock()
	if serviceStatus, ok1 := containersStatus.data[serviceName]; ok1 {
		if slotContainerID, ok2 := serviceStatus[serviceSlot]; ok2 {
			containersStatus.RUnlock()
			return slotContainerID, true
		}
	}
	containersStatus.RUnlock()
	return "", false
}


func (containersStatus ContainersStatus) ContainerDied(serviceName string, serviceSlot int) {
	containersStatus.Lock()
	if service, ok1 := containersStatus.data[serviceName]; ok1 {
		if _, ok2 := service[serviceSlot]; ok2 {
			delete(service, serviceSlot)
		} else {
			fmt.Println("ERROR", "slot did not exist in ContainersStatus")
			// really should not have happened..
			// if a container dies it must appear in the system..
		}
	} else {
		fmt.Println("ERROR", "service did not exist in ContainersStatus")
		// really should not have happened..
		// if a container dies it must appear in the system..
	}
	containersStatus.Unlock()
}

func (containersStatus ContainersStatus) ContainerBorn(serviceName string, serviceSlot int, containerID string ) {
	containersStatus.Lock()
	if service, ok1 := containersStatus.data[serviceName]; ok1 {
		service[serviceSlot] = containerID
	} else {
		// ... damn service did not exist yet..
		// all services should be loaded at the beggining of an experiment..
		// TODO load services at beggining of experiment, with help of service_start numbers
		containersStatus.data[serviceName] = make(map[int]string)
		containersStatus.data[serviceName][serviceSlot] = containerID
	}
	containersStatus.Unlock()
}

func (containersStatus ContainersStatus) InitializeService(serviceName string) {
	containersStatus.Lock()
	if _, ok1 := containersStatus.data[serviceName]; ok1 {
		//nothing to do
	} else {
		containersStatus.data[serviceName] = make(map[int]string)
	}
	containersStatus.Unlock()
}




