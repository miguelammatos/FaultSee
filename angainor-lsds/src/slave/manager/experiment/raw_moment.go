package experiment

import (
	"fmt"
	"slave/manager/debug"
)

const MOMENT_SPACES = "     "

// ExperimentMoment consists of a moment in time which some actions will be executed
type RawMoment interface {
	time() int //moment of
	validate() error
	build(raw interface{}) error
	importIntoExperiment(creator *experimentIterator, translator TranslateServiceSlot) error
}

// experimentBeginning is one type of experimentMoment
// it describes the initial state of the experiment
// @InitialValues maps the number of items for each service (key of map)
type experimentBeginning struct {
	InitialValues map[string]int `yaml:"beginning"`
}

// experimentEnd is one type of experimentMoment
// it describes the moment at which the experiment ends
type experimentEnd struct {
	Time int `yaml:"end"`
}

// auxExperimentFault is used as auxiliary in yaml parsing of experimentFault
type auxExperimentMoment struct {
	Time   int `yaml:"time"`
	Mark   string
	Services map[string][](map[string]interface{})
}

// ExperimentFault is one type of experimentMoment
// it describes the holds the information regarding faults to inject in a given moment
type experimentMoment struct {
	Time   int
	Mark   string
	Services map[string]([]RawServiceEvent)
}

func (value *experimentBeginning) time() int {
	return 0
}
func (value *experimentEnd) time() int {
	return value.Time
}
func (value *auxExperimentMoment) time() int {
	return value.Time
}
func (value *experimentMoment) time() int {
	return value.Time
}

func (value *experimentBeginning) build(raw interface{}) error {
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("ParseMoment: Error Building %s. Error: %v. Input: %s", typeof(value), err, raw)
		return err2
	}
	debug.ParseChurnDebug(MOMENT_SPACES, typeof(value), value)
	return nil
}
func (value *experimentEnd) build(raw interface{}) error {
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("Error Building %s. Error: %v. Input: %s", typeof(value), err, raw)
		return err2
	}
	debug.ParseChurnDebug(MOMENT_SPACES, typeof(value), value)
	return nil
}
func (value *auxExperimentMoment) build(raw interface{}) error {
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("Error Building %s. Error: %v. Input: %s", typeof(value), err, raw)
		return err2
	}
	debug.ParseChurnDebug(MOMENT_SPACES, typeof(value), value)
	return nil
}

func (value *experimentMoment) build(raw interface{}) error {
	var experimentMoment auxExperimentMoment
	if err := experimentMoment.build(raw); err != nil {
		err2 := fmt.Errorf("Error Building %s. Error: %v", typeof(value), err)
		return err2
	}
	services, err := buildEventsArray(experimentMoment.Services)
	if err != nil {
		err2 := fmt.Errorf("Error Building %s. %v", typeof(value), err)
		return err2
	}
	value.Time = experimentMoment.Time
	value.Mark = experimentMoment.Mark
	value.Services = services
	debug.ParseChurnDebug(MOMENT_SPACES, typeof(value), value)
	return err
}

func (value *experimentBeginning) validate() error {
	// All services start number must be provided
	// They can automatically be inputed by MASTER
	// This validation is Not required here. It will be done later. When we know all the services that need fault injection

	// if len(value.InitialValues) != 0 {
	// 	err := fmt.Errorf("ParseMoment: Error Building %s. At least one service start numbers must be provided. Input: %s", typeof(value), err, raw)
	// 	return err
	// }
	return nil
}
func (value *experimentEnd) validate() error {
	if value.time() == 0 {
		err := fmt.Errorf("ParseMoment: Error Building %s. Experiment end must be bigger than zero. Input: %v", typeof(value), value)
		return err
	}
	return nil
}
func (value *experimentMoment) validate() error {
	if value.time() == 0 {
		err := fmt.Errorf("ParseMoment: Error Building %s. Fault Times must be bigger than zero. Input: %v", typeof(value), value)
		return err
	}
	return nil
}

func importRawMoment(element map[string]interface{}) (RawMoment, error) {
	for momentType := range element {
		debug.ParseChurnDebug(" ", momentType)
		switch momentType {
		case "beginning":
			var expBeginning experimentBeginning
			if err := expBeginning.build(element); err != nil {
				err2 := fmt.Errorf("ParseMoment: type %s: error '%v'", momentType, err)
				return nil, err2
			}
			return &expBeginning, nil
		case "end":
			var expEnd experimentEnd
			if err := expEnd.build(element); err != nil {
				err2 := fmt.Errorf("ParseMoment: type %s: error '%v'", momentType, err)
				return nil, err2
			}
			return &expEnd, nil
		case "moment":
			var expAction experimentMoment
			if err := expAction.build(element[momentType]); err != nil {
				err2 := fmt.Errorf("ParseMoment: type %s: error '%v'", momentType, err)
				return nil, err2
			}
			return &expAction , nil

		default:
			err := fmt.Errorf("ParseMoment: '%s' not support as moment type.Input: %s", momentType, element)
			return nil, err
		}
	}
	err := fmt.Errorf("ParseMoment: CRITICAL ERROR, Return only present to satisfy compiler. If this error message is ever presented to you please revise the code. Input: %s", element)
	return nil, err

}
