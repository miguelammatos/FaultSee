package experiment

import (
	"fmt"
	"log"
	"reflect"
	"strconv"

	yaml "gopkg.in/yaml.v2"
)

// ParseIntoCorrectStruct takes interface, marshals back to []byte,
// then unmarshals to desired struct
// It is an hack that allows to parse yaml
// When different structs can be present in the same place,
// this allows to construct the right one
func ParseIntoCorrectStruct(structIn, structOut interface{}) error {
	b, err := yaml.Marshal(structIn)
	if err != nil {
		return err
	}
	return yaml.Unmarshal(b, structOut)
}

// typeof used in logging
func typeof(v interface{}) string {
	return reflect.TypeOf(v).String()
}

// churn is a struture that holds a whole experiment
type auxChurn struct {

	Environment map[string]string
	Events      []map[string]interface{}
}

func parseEnvironment(options map[string]string) (int64, error){
	fmt.Println("Environment Parse ", options)


	for key, option := range options {
		fmt.Println(key, " -> ", option)
		if key == "seed" {
			return strconv.ParseInt(option, 10, 64)
		}
	}
	return 789, nil
}

// parseChurn transforms a script (as a string) into Moments that can be transformed into actions
// returns the array of moments, the uint64 that is going to be the seed
func parseChurn(stringChurn string) ([]RawMoment, int64, error) {
	//log.Println("Will PARSE")
	//log.Println(stringChurn)
	chu := auxChurn{}
	err := yaml.Unmarshal([]byte(stringChurn), &chu)
	if err != nil {
		err2 := fmt.Errorf("Error while unmarshal churn '%v'. Input: %s", err, stringChurn)
		return nil, 0, err2
	}
	log.Println(chu)
	var experiment []RawMoment
	for _, element := range chu.Events {
		//check if map
		// TODO maybe
		//we only need

		expElement, err := importRawMoment(element)
		if err != nil {
			err2 := fmt.Errorf("Trying to parse moment: Error %v", err)
			return nil, 0, err2
		}
		experiment = append(experiment, expElement)
	}

	seedNumber, err := parseEnvironment(chu.Environment)

	return experiment, seedNumber, err
}

func EntryThemain(){
	parseChurn(example_churn_string)
}

// RawMoments asd
type RawMoments []RawMoment

// Required functions to apply sort.Sort()
func (s RawMoments) Len() int             { return len(s) }
func (s RawMoments) Swap(i, j int)        { s[i], s[j] = s[j], s[i] }
func (s RawMoments) Iterate() []RawMoment { return s }
func (s RawMoments) Less(i, j int) bool   {
	return s[i].time() < s[j].time()
}
