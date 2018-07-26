package experiment

import (
	// "fmt"
	"fmt"
	"slave/manager/experiment/ActionsIdManager"
	"slave/utils/bubble_sort"

	"sort"


	// fmt "github.com/kr/pretty"
)


type serviceReplicas struct {

}

type experimentIterator struct {
	currentReplicasNumber map[string]serviceReplicasHolder //holds the number of containers for each service
	endMoment             int
	actions               []executableEvent
}

// Kinda like visitor pattern..
func (value *experimentEnd) importIntoExperiment(creator *experimentIterator, _ TranslateServiceSlot) error {
	creator.endMoment = value.time()
	endMoment := &EndMoment{
		executableEventStruct: executableEventStruct{
			Time: value.time(),
			ProcessedInThisNode:false,
			Id: ActionsIdManager.NextAvailableID(),
		},
	}
	creator.actions = append(creator.actions, endMoment)
	return nil
}

func (value *experimentBeginning) importIntoExperiment(creator *experimentIterator, _ TranslateServiceSlot) error {
	for serviceName, startReplicas := range value.InitialValues {
		creator.currentReplicasNumber[serviceName] = createServiceReplicasHolder(startReplicas)
	}
	startExperimentMarker := &BeginningMoment{
		executableEventStruct: executableEventStruct{
			ProcessedInThisNode:true,
			Id: ActionsIdManager.NextAvailableID(),
			Time:0,
		},
	}
	creator.actions = append(creator.actions, startExperimentMarker)

	return nil
}

func (value *experimentMoment) importIntoExperiment(creator *experimentIterator, translator TranslateServiceSlot) error {
	if len(value.Services) == 0{
		if value.Mark != "" {
			// Whenever we have a mark we to create this action
			markMomentAction := &MarkMoment{
				executableEventStruct: executableEventStruct{
					Time: value.Time,
					ProcessedInThisNode:false,
					Id: ActionsIdManager.NextAvailableID(),
				},
				CustomMessage: value.Mark,
			}
			creator.actions = append(creator.actions, markMomentAction)
		}
	}
	keys := make([]string, 0)
	for key := range value.Services {
		keys = append(keys, key)
	}
	// sort by ServiceName
	sort.Strings(keys)

	for _, serviceName := range keys {
	//for serviceName, actionsArray  := range value.Services {
		actionsArray := value.Services[serviceName]
		for _, action := range actionsArray {
			actions, err := action.createExecutableEvent(&creator.currentReplicasNumber, translator, serviceName, value.time())
			if err != nil {
				return err
			} else {
				// go does not allow to append all at once, complains about type mismatch
				for _, executableAction := range actions {
					creator.actions = append(creator.actions, executableAction)
				}
			}
		}
	}

	return nil
}

// importRawMoments receives an array of Moments and processes them
// into containerMoment. One moment contains one or multiple actions
func importRawMoments(arrayRawMoments RawMoments, translator TranslateServiceSlot) ([]executableEvent, error) {
	// sort array
	//bubbleSort used in order to control the sort algorithm
	//we will use bubble sort in master and slave
	//no need to worry about performance because this only runs once per round,
	//and with few items, generally already sorted
	bubble_sort.BubbleSort(arrayRawMoments)


	// not all events will translate to slave moments
	// but most will
	numberMoments := len(arrayRawMoments)
	creator := experimentIterator{
		currentReplicasNumber: make(map[string]serviceReplicasHolder),
		actions:               make([]executableEvent, 0, numberMoments),
	}
	for _, executableAction := range arrayRawMoments {
		err := executableAction.importIntoExperiment(&creator, translator)
		if err != nil {
			err2 := fmt.Errorf("Error: %v. Trying to import Event: %s", err, executableAction )
			return nil, err2
		}
	}
	// pretty.Println("ALL FAULTS", creator.faults)
	return creator.actions, nil
}
