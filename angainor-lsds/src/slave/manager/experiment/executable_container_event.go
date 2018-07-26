package experiment

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"slave/manager/faults"
	"time"

	"github.com/docker/engine/client"
)

type injectInContainerInterface interface {
	createMarkMessage() string
	InjectorString() string
	applyActionToContainer(dockerClient *client.Client, slotContainerID string) error

}

// executableContainerEvent describes moments in which an action takes place against a container
type executableContainerEvent interface {
	injectInContainerInterface

	//-----------------------------------
	// ExecutableMoment methods
	//-----------------------------------
	String() string
	beProcessed(manager *Manager) error
	time() int
	dryRun() string
	processedByThisNode() bool
	ID() int
	restartProcessed()
//-----------------------------------

	// specific container identification
	serviceName() string
	serviceSlot() int
}

// Hack to avoid Duplicate Method when inheriting from two interfaces that have a method in common
// This have provides a compilation time verification that executableContainerEvent implements executableEvent
func MakeSureExecutableContainerEventIsAnExecutableEvent (moment executableContainerEvent){
	makeSureExecutableEvent(moment)
}

type executableContainerEventStruct struct {
	executableEventStruct
	//Promise Implementing applyAction
	injectInContainerInterface

	_serviceName string
	_serviceSlot int
}


func (value *executableContainerEventStruct) beProcessed(manager *Manager) error{
	serviceName := value.serviceName()
	serviceSlot := value.serviceSlot()
	if slotContainerID, isPresent := manager.containerStatus.ContainerPresent(serviceName, serviceSlot) ; isPresent {
			// compiler was not respecting moment.String was called inside log.PrintLn
			log.Println("RUN: Applying ", value.String())
			err := value.applyActionToContainer(manager.dockerCli, slotContainerID)

			//return err
			if err != nil {
				return err
			}
			value.ProcessedInThisNode = true
			//else {
			manager.marksOutput <- value.createMarkMessage()
			return nil
	}
	// else simply ignore it
	log.Println("RUN: Container not present, ignoring moment ", value.String())
	return nil
}


func NewExecutableContainerMoment(executableMomentStruct executableEventStruct, injector injectInContainerInterface, serviceName string, serviceSlot int) *executableContainerEventStruct {
	return &executableContainerEventStruct{
		executableMomentStruct,
		injector,
		serviceName,
		serviceSlot,
	}
}

func (value *executableContainerEventStruct) serviceName() string { return value._serviceName  }
func (value *executableContainerEventStruct) serviceSlot() int    { return value._serviceSlot }

func (value executableContainerEventStruct) String() string {
	return fmt.Sprint(value.executableEventStruct.TimeString(), " container: ", value.serviceName(), ":", value.serviceSlot(), " Injector: ", value.InjectorString())
}

func (value *executableContainerEventStruct) dryRun() string{
	return fmt.Sprintf("Time: %d | service: %s ; slot: %d | Injector: %s", value.Time, value.serviceName(), value.serviceSlot(),  value.InjectorString())
}

//----------------------------------------------//
//----------------------------------------------//
//----------------------------------------------//
type injectFaultWorker struct {
	Details faults.FaultDetails
}

func (value injectFaultWorker) InjectorString() string {
	return fmt.Sprint(" FaultDetails: ", value.Details)
}

func (value injectFaultWorker) createMarkMessage() string {
	faultDetailsJSON, err := json.Marshal(value.Details.FaultScriptFileName)
	if err != nil {
		log.Println(err)
		return fmt.Sprintf ("{ \"moment\": \"%s\" ; \"error\" : \"transforming FaultScriptFileName to JSON\"}", "fault")
	}
	return fmt.Sprintf ("{ \"type\": \"event\", \"moment\": \"%s\", \"script\" : %s }", "fault", faultDetailsJSON)
}

func (value injectFaultWorker) applyActionToContainer(dockerClient *client.Client, slotContainerID string) error {
	err := faults.InjectFaultOnContainer(dockerClient, slotContainerID, value.Details)
	return err
}

//----------------------------------------------//
//----------------------------------------------//
//----------------------------------------------//
type sendSignalWorker struct {
	Signal string
}

func (value sendSignalWorker) InjectorString() string {
	return fmt.Sprint(" Signal: ", value.Signal)
}

func (value sendSignalWorker) createMarkMessage() string {
	signalJSON, err := json.Marshal(value.Signal)
	if err != nil {
		log.Println(err)
		return fmt.Sprintf ("{ \"moment\": \"%s\" ; \"error\" : \"transforming Signal to JSON\"}", "SendSignal")
	}
	return fmt.Sprintf ("{ \"type\": \"event\", \"moment\": \"%s\", \"signal\" : %s }", "SendSignal", signalJSON)
}

func (value sendSignalWorker) applyActionToContainer(dockerClient *client.Client, slotContainerID string) error {
	err := faults.SendSignalToContainer(dockerClient, slotContainerID, value.Signal)
	return err
}


//----------------------------------------------//
//----------------------------------------------//
//----------------------------------------------//
type stopContainerWorker struct {}

func (value stopContainerWorker) InjectorString() string {
	return fmt.Sprint(" Stop gracefully")
}

func (value stopContainerWorker) createMarkMessage() string {
	return fmt.Sprintf ("{ \"type\": \"event\", \"moment\": \"%s\" }", "Stop Container Gracefully")
}

func (value stopContainerWorker) applyActionToContainer(dockerClient *client.Client, slotContainerID string) error {
	timeout := 10 * time.Second
	err := dockerClient.ContainerStop(context.Background(), slotContainerID, &timeout)
	return err
}