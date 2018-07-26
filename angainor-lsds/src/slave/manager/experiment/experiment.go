package experiment

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"slave/manager/container_status"
	"slave/manager/experiment/ActionsIdManager"
	"strings"
	"time"

	"github.com/docker/engine/client"
	"slave/manager/debug"
	"slave/manager/events"
)



// Manager performs experiment actions
// cli is docker client
// in is a channel that receives docker events
type Manager struct {
	experimentActions 		[]executableEvent
	parseFunction     		GetServiceSlotFromEvent
	transtaleSlotFunction   TranslateServiceSlot
	containerStatus   		container_status.ContainersStatus
	dockerCli         		*client.Client
	input             		<-chan string
	output            		chan<- string
	marksOutput       		chan<- string
	experimentLoaded		bool
}

// New Creates Manager
func New(cli *client.Client, input <-chan string, output chan<- string, marksOutput chan<- string, orchestrator string) *Manager {
	return &Manager{
		dockerCli:       cli,
		input:           input,
		output:          output,
		marksOutput: 	 marksOutput,
		parseFunction:   GetFunctionGetServiceSlot(orchestrator),
		transtaleSlotFunction: GetFunctionTranslateSlot(orchestrator),
		containerStatus: container_status.CreateEmptyContainerStatus(),
	}
}


// Validates theres is an experiment parsed
// Everytime a new parse starts this value becomes false until the parse completes
func (manager *Manager) ExperimentReady() bool {
	return manager.experimentLoaded
}

func (manager *Manager) processMoment(moment executableEvent) {
	err := moment.beProcessed(manager)
	if err != nil {
		fmt.Println("ERROR", "Applying moment ", moment.String(), " err: ", err)
		fmt.Println("ERROR", "Shamelessly continuing..")
		manager.output <- fmt.Sprint("ERROR", "Applying moment ", moment.String(), " err: ", err)
	}
}


func (manager *Manager) dryRunMoment(moment executableEvent) {
	momentDescription := moment.dryRun()
	manager.output <- momentDescription
	log.Println("Moment Applied: ", momentDescription)
}

// PrepareExperiment receives an string with churn and creates the imports into structures
// that slave can then use during the experiement
func (manager *Manager) PrepareExperiment(experimentChurn string) error {

	// Important Step
	ActionsIdManager.Reset()
	manager.experimentLoaded = false

	arrayMoments, randomSeed, err := parseChurn(experimentChurn)
	if err != nil {
		err2 := fmt.Errorf("Parsing Churn. Error '%v'", err)
		return err2
	}
	log.Println("Using SEED", randomSeed)
	rand.Seed(randomSeed)
	log.Println("PARSE_CHURN: Churn parsed with success")
	slaveExecutableActions, err := importRawMoments(arrayMoments, manager.transtaleSlotFunction)
	if err != nil {
		err2 := fmt.Errorf("Importing moments. Error '%v'", err)
		return err2
	}

	log.Println("PARSE_CHURN: Moments imported into experiment with success")
	manager.experimentActions = slaveExecutableActions
	fmt.Printf("All Events:\n")
	for _, action := range manager.experimentActions {
		fmt.Printf("\t  %+v\n", action)
	}
	manager.experimentLoaded = true

	return nil
}

// PlayRun runs a previous loaded run
func (manager *Manager) PlayRun(ctx context.Context, startAt time.Time) {
	difference := startAt.Sub(time.Now())
	time.Sleep(difference)

	log.Println("RUN: Starting Run")
	moments := manager.experimentActions
	currentMoment := 0
	for _, moment := range moments {
		momentToApply := moment.time()
		if currentMoment < momentToApply {
			sleepSeconds := momentToApply - currentMoment
			log.Println("Sleeping Until next action in", sleepSeconds)
			time.Sleep(time.Second * time.Duration(sleepSeconds))
		}
		currentMoment = momentToApply
		go manager.processMoment(moment)
		//go moment.beProcessed(manager)
	}
	log.Println("RUN: We reached the end of the run. All moments processes were started. Sleeping 10 seconds")
	time.Sleep(time.Second * 10)

	// for tick := range time.Tick(1 * time.Second) {
	// 	go processTick(tick, )
	// }
}


// PlayRun runs a previous loaded run
func (manager *Manager) DryRun() {
	log.Println("DRY RUN: Starting Run")
	moments := manager.experimentActions
	currentMoment := 0
	for _, moment := range moments {
		momentToApply := moment.time()
		if currentMoment < momentToApply {
			sleepSeconds := momentToApply - currentMoment
			log.Println("Sleeping Until next action in", sleepSeconds)
			manager.output <- fmt.Sprintln("Sleep ", sleepSeconds, " seconds")
		}
		currentMoment = momentToApply
		manager.dryRunMoment(moment)
		//go moment.beProcessed(manager)
	}
	log.Println("DRY RUN: We reached the end of the run. All moments processes were started. Sleeping 10 seconds")
	time.Sleep(time.Second * 10)
}

func (manager *Manager) containerStarted(serviceName string, serviceSlot int, containerID string) {
	debug.ContainersAliveDeadDebug("  ", "  ", time.Now().Format(time.RFC3339Nano), "ALIVE", "serviceName: ", serviceName, "slot: ", serviceSlot, "Container: ", containerID)
	manager.containerStatus.ContainerBorn(serviceName, serviceSlot, containerID)
}
func (manager *Manager) containerDied(serviceName string, serviceSlot int) {
	debug.ContainersAliveDeadDebug("  ", "  ", time.Now().Format(time.RFC3339Nano), " DEAD", "serviceName: ", serviceName, "slot: ", serviceSlot)
	manager.containerStatus.ContainerDied(serviceName,serviceSlot)
}

// ParseDockerEvent is responsible for interpreting docker events that may be relevant
func (manager *Manager) ParseDockerEvent(event events.Entry) {
	if event.Type == "container" {
		if event.Status == "start" {
			// fmt.Println("  ", "Container START EVENT")
			serviceName, serviceSlot, containerID, err := manager.parseFunction(event)
			if err != nil {
				// probably container did not belong to experiment
				// lets alert create a log msg nonetheless
				manager.output <- fmt.Sprint("Ignoring Container Start Event: ", err.Error())
			} else {
				manager.containerStarted(serviceName, serviceSlot, containerID)
			}
		} else if event.Status == "die" {
			// fmt.Println("  ", "Container DIE EVENT")
			serviceName, serviceSlot, _, err := manager.parseFunction(event)
			if err != nil {
				// probably container did not belong to experiment
				// lets alert create a log msg nonetheless
				manager.output <- fmt.Sprint("Ignoring Container Die Event: ", err.Error())
			} else {
				manager.containerDied(serviceName, serviceSlot)
			}
		}
	}
}

func (manager *Manager) ResetRound() {
	log.Println("Reseting Round")
	for _, action := range manager.experimentActions {
		action.restartProcessed()
	}
}


// returns a json string with all events
func (manager *Manager) GetProcessedEvents() string {
	var sb strings.Builder
	sb.WriteString("[")
	prefix := "{"
	suffix := "}"
	comma := ""
	//var jsEnc json.Encoder
	//jsEnc = json.Encoder{}
	//jsEnc.Encode()
	for _, action := range manager.experimentActions {
		sb.WriteString(comma)
		comma = ","
		jsonStruct := struct {
			ID int
			Action string
			Processed bool
		}{
			ID: action.ID(),
			Action: action.createMarkMessage(),
			Processed: action.processedByThisNode(),
		}

		var jsonData []byte
		jsonData, err := json.Marshal(jsonStruct)
		if err != nil {
			log.Println(err)
			sb.WriteString(prefix)
			sb.WriteString("\"error\": ")
			sb.WriteString(fmt.Sprintf("%s", err.Error()))
			sb.WriteString(suffix)
		} else {
			sb.WriteString(string(jsonData))
		}

	}
	sb.WriteString("]")
	return sb.String()
}

