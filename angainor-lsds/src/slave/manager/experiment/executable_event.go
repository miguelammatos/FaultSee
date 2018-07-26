package experiment

import (
	"encoding/json"
	"fmt"
	"log"
)

type createMarkInterface interface {
	// All events are recorded in the final log file, this method specifies what information is recorded
	// For ease of parsing, it is recommend to return a JSON compatible string
	createMarkMessage() string
}

// executableEvent describes moments in which slaves need to take action
type executableEvent interface {
	createMarkInterface

	// Better logging
	String() string

	// Method that executes the moment
	beProcessed(manager *Manager) error

	// method that returns a string describing the moment
	dryRun() string

	// Moment at which moment is executed
	time() int

	// this will tell if the event was processed here
	processedByThisNode() bool

	// this will restart if the event was processed
	restartProcessed()

	// an integer that represents the order in which the action is applied
	ID() int

}

//Hack
func makeSureExecutableEvent(_ executableEvent){
	// we just want to make the compiler verify that the passed argument implements all interface methods
}

type executableEventStruct struct {
	Time int
	ProcessedInThisNode bool
	Id int
}

func (value *executableEventStruct) time() int { return value.Time  }
// We want everything to be properly logged, so we will not Implement String() method here
func (value executableEventStruct) TimeString() string {
	return fmt.Sprint("Time: ",value.time(), "s")
}
func (value executableEventStruct) processedByThisNode() bool {
	return value.ProcessedInThisNode
}
func (value executableEventStruct) restartProcessed() {
	value.ProcessedInThisNode = false
}
func (value executableEventStruct) ID() int {
	return value.Id
}

//----------------------------------------------//
//----------------------------------------------//
//----------------------------------------------//
// EndMoment marks the end of an experiment
type EndMoment struct {
	executableEventStruct
}

func (value *EndMoment) String() string {
	return fmt.Sprint("End Experiment ", value.time(), "s")
}

func (value *EndMoment) createMarkMessage() string {
	return fmt.Sprintf ("{ \"type\": \"event\", \"moment\": \"%s\" }", "end")
}

func (value *EndMoment) beProcessed(manager *Manager) error{
	value.ProcessedInThisNode = true
	manager.marksOutput <- value.createMarkMessage()
	log.Println("Experiment End Processed")
	return nil
}
func (value *EndMoment) dryRun() string{
	return fmt.Sprintf("End: %ds", value.Time)
}
//----------------------------------------------//
//----------------------------------------------//
//----------------------------------------------//
// BeginningMoment marks the start of an experiment
type BeginningMoment struct {
	executableEventStruct
}

func (value *BeginningMoment) String() string {
	return fmt.Sprint("Start Experiment ")
}

func (value *BeginningMoment) createMarkMessage() string {
	return fmt.Sprintf ("{ \"type\": \"event\",  \"moment\": \"%s\" }", "beggining")
}

func (value *BeginningMoment) beProcessed(manager *Manager) error{
	log.Println("Experiment Start Processed")
	value.ProcessedInThisNode = true
	manager.marksOutput <- value.createMarkMessage()
	return nil
}


func (value *BeginningMoment) dryRun() string{
	return fmt.Sprintf("Beginning")
}

//----------------------------------------------//
//----------------------------------------------//
//----------------------------------------------//
// MarkMoment stores the information when a Mark needs to be injected
type MarkMoment struct {
	executableEventStruct
	CustomMessage string
}

func (value *MarkMoment) String() string {
	return fmt.Sprint(value.executableEventStruct.TimeString(), " Marking Moment ", value.CustomMessage)
}

func (value *MarkMoment) createMarkMessage() string {
	customMessage, err := json.Marshal(value.CustomMessage)
	if err != nil {
		log.Println(err)
		return fmt.Sprintf ("{ \"moment\": \"%s\" , \"error\" : \"transforming message to JSON\"}", "mark")
	}
	return fmt.Sprintf ("{ \"type\": \"mark\", \"moment\": \"%s\" , \"message\" : %s}", "mark", customMessage)
}

func (value *MarkMoment) beProcessed(manager *Manager) error{
	manager.marksOutput <- value.createMarkMessage()
	value.executableEventStruct.ProcessedInThisNode = true
	log.Println("Mark", value.String(), " Processed")
	return nil
}

func (value *MarkMoment) dryRun() string{
	return fmt.Sprintf("Time: %d | Message: %s", value.Time, value.CustomMessage)
}

//----------------------------------------------//
//----------------------------------------------//
//----------------------------------------------//
// MarkMoment stores the information when a Mark needs to be injected
type StartContainersMoment struct {
	executableEventStruct
	serviceName string
	numberContainers int
}

func (value *StartContainersMoment) String() string {
	return fmt.Sprint(value.executableEventStruct.TimeString(), " ", value.serviceName, ": Start ", value.numberContainers, "Containers")
}

func (value *StartContainersMoment) createMarkMessage() string {
	serviceNameJSON, err := json.Marshal(value.serviceName)
	if err != nil {
		log.Println(err)
		return fmt.Sprintf ("{ \"moment\": \"%s\" , \"error\" : \"transforming serviceName to JSON\"}", "Start")
	}
	return fmt.Sprintf ("{ \"type\": \"event\", \"moment\": \"%s\" , \"Service\" : %s, \"amount\" : %d }", "Start Containers", serviceNameJSON, value.numberContainers)
}

func (value *StartContainersMoment) beProcessed(manager *Manager) error{
	manager.marksOutput <- value.createMarkMessage()
	// we only need to mark the event
	// this is processed in Master Node Only
	value.executableEventStruct.ProcessedInThisNode = false
	log.Println("Mark", value.String(), " Processed")
	return nil
}

func (value *StartContainersMoment) dryRun() string{
	return fmt.Sprintf("Time: %d | Service %s Amount: %d  containers", value.Time, value.serviceName, value.numberContainers)
}