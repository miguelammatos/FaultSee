package experiment

import (
	"errors"
	"fmt"
	"log"
	"strconv"
	"strings"

	"slave/manager/events"
	"slave/manager/support"
)

// GetServiceSlotFromEvent Type of functions that will return which container an event is refering to
// Usefull to achieve docker-swarm and kubernetes compatibility
type GetServiceSlotFromEvent func(event events.Entry) (serviceName string, serviceSlot int, containerID string, err error)
type TranslateServiceSlot func(internalIndex int) (slot int, err error)

// GetFunction fetches the function that will extract container information from docker event
func GetFunctionGetServiceSlot(orchestrator string) GetServiceSlotFromEvent {
	if !support.Supports(orchestrator) {
		// PANIC
		log.Fatalf("FATAL: %s is not a supported orchestrator", orchestrator)
	}
	switch orchestrator {
	case "docker-swarm":
		return dockerSwarmEventParser
	}
	//PANIC
	log.Fatalf("FATAL: Execution flow Bug. %s is considered a supported orchestrator, but no GetServiceSlotFromEvent function was found", orchestrator)
	return nil // compiler requirement, log.FATALF will call os.exit
}

// GetFunction fetches the function that will extract container information from docker event
func GetFunctionTranslateSlot(orchestrator string) TranslateServiceSlot {
	if !support.Supports(orchestrator) {
		// PANIC
		log.Fatalf("FATAL: %s is not a supported orchestrator", orchestrator)
	}
	switch orchestrator {
	case "docker-swarm":
		return dockerSwarmSlotTranslator
	}
	//PANIC
	log.Fatalf("FATAL: Execution flow Bug. %s is considered a supported orchestrator, but no GetServiceSlotFromEvent function was found", orchestrator)
	return nil // compiler requirement, log.FATALF will call os.exit
}



func dockerSwarmEventParser(event events.Entry) (serviceName string, serviceSlot int, containerID string, err error) {
	// pretty.Println("ATRIBUTeS", event.Actor.Attributes)
	// for key, value := range event.Actor.Attributes {
	// pretty.Println(key, "->", value)
	// }
	if isExperimentContainer, ok := event.Actor.Attributes["org.faultsee.experiment.container"]; !ok || isExperimentContainer != "true" {
		// fmt.Println("OK", ok)
		// fmt.Println("isExperimentContainer", isExperimentContainer)
		err = fmt.Errorf("Ignoring Container: Not from experiment.. ID: %s", event.Actor.ID)
		return // default values and err
	}
	if containerName, ok := event.Actor.Attributes["com.docker.swarm.task.name"]; ok {
		// example of container name: "simple_http.1.irxszgnliqiqqel9qf2s0gyj1"
		containerNameArray := strings.Split(containerName, ".")
		if len(containerNameArray) != 3 {
			err = fmt.Errorf("Expecting container name of type: 'simple_http.1.irxszgnliqiqqel9qf2s0gyj1', found %s", containerName)
			return // default values and err
		}
		containerID = event.ID
		serviceName = containerNameArray[0]
		serviceSlot, err = strconv.Atoi(containerNameArray[1])
		return serviceName, serviceSlot, containerID, err
	}
	err = errors.New("Could not process event to gather service Name and Slot [docker-swarm]")
	return // default values and err
}

func dockerSwarmSlotTranslator(internalIndex int) (int,error) {
	if internalIndex < 0 {
		err := fmt.Errorf("Internal Index must be 0 or bigger")
		return -1, err
	}
	return internalIndex + 1, nil
}
