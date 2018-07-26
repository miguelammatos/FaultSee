package experiment

import (
	"fmt"
	"slave/manager/debug"
	"slave/manager/experiment/ActionsIdManager"
	"strconv"
	"strings"

	"slave/manager/faults"
)

const action_spaces = "          "

// Moment docs
type RawServiceEvent interface {
	target() eventTarget
	createExecutableEvent(currentReplicas *map[string]serviceReplicasHolder, translator TranslateServiceSlot, serviceName string, time int) ([]executableEvent, error)
}

type sendSignal struct {
	RawReplicas    		 map[string]interface{} `yaml:"target"`
	ParsedReplicas 		 eventTarget            `yaml:"-"`
	SignalStruct struct {
		RawKillsContainer    string   				`yaml:"kills_container"`
		KillsContainer		 bool     				`yaml:"-"`
		Signal         		 string
	}	`yaml:"signal"`
}
// Not used, but needs to be here, so we can parse the script
type stop struct {
	RawReplicas    map[string]interface{} `yaml:",inline"`
	ParsedReplicas eventTarget                 `yaml:"-"`
}
type start struct {
	RawReplicas    map[string]interface{} `yaml:",inline"`
	ParsedReplicas eventTarget                 `yaml:"-"`
}

type customFault struct {
	RawReplicas          map[string]interface{} `yaml:"target"`
	ParsedReplicas       eventTarget    		`yaml:"-"`
	Custom struct{
		FaultFileName        string         		`yaml:"fault_file_name"`
		FaultFileFolder      string        			`yaml:"fault_file_folder"`
		Executable           string
		RawKillsContainer    string   				`yaml:"kills_container"`
		KillsContainer		 bool     				`yaml:"-"`
		ExecutableArguments  []string 				`yaml:"executable_arguments"`
		FaultScriptArguments []string 				`yaml:"fault_script_arguments"`
	}
}

//type ArrayRawServiceEvent []RawServiceEvent
//
//// Required functions to apply sort.Sort()
//func (s ArrayRawServiceEvent) Len() int             { return len(s) }
//func (s ArrayRawServiceEvent) Swap(i, j int)        { s[i], s[j] = s[j], s[i] }
//func (s ArrayRawServiceEvent) Iterate() []RawServiceEvent { return s }
//func (s ArrayRawServiceEvent) Less(i, j int) bool   {
//	return s[i].comparissonString() < s[j].comparissonString()
//}
//
//func (value *stop) comparissonString() string {
//	return fmt.Sprintf("%s ;  TARGET -> %s", value.target().String())
//}
//func (value *start) comparissonString() string {
//	return fmt.Sprintf("Start TARGET -> %s", value.target().String())
//}
//func (value *sendSignal) comparissonString() string {
//	return fmt.Sprintf("Send Signal <%s> to TARGET -> %s (KILLS? %v)", value.SignalStruct.Signal, value.target().String(), value.SignalStruct.KillsContainer)
//}
//func (value *customFault) comparissonString() string {
//	return fmt.Sprintf("Fault <%s> to TARGET -> %s (KILLS? %v)", value.Custom.FaultFileName, value.target().String(), value.Custom.KillsContainer)
//
//}


func (value *stop) String() string {
	return fmt.Sprintf("Stop TARGET -> %s", value.target().String())
}
func (value *start) String() string {
	return fmt.Sprintf("Start TARGET -> %s", value.target().String())
}
func (value *sendSignal) String() string {
	return fmt.Sprintf("Send Signal <%s> to TARGET -> %s (KILLS? %v)", value.SignalStruct.Signal, value.target().String(), value.SignalStruct.KillsContainer)
}
func (value *customFault) String() string {
	return fmt.Sprintf("Fault <%s> to TARGET -> %s (KILLS? %v)", value.Custom.FaultFileName, value.target().String(), value.Custom.KillsContainer)

}

// TODO put all valid signals here
var VALID_KILL_SIGNALS = [...]string{"SIGHUP", "SIGINT", "SIGQUIT", "SIGILL", "SIGTRAP", "SIGABRT", "SIGIOT", "SIGBUS", "SIGEMT", "SIGFPE", "SIGKILL", "SIGUSR1", "SIGSEGV", "SIGUSR2", "SIGPIPE", "SIGALRM", "SIGTERM", "SIGSTKFLT", "SIGCHLD", "SIGCLD", "SIGCONT", "SIGSTOP", "SIGTSTP", "SIGTTIN", "SIGTTOU", "SIGURG", "SIGXCPU", "SIGXFSZ", "SIGVTALRM", "SIGPROF", "SIGWINCH", "SIGIO", "SIGPOLL", "SIGPWR", "SIGINFO", "SIGLOST", "SIGSYS", "SIGUNUSED"}

func (value *sendSignal) validateSignal() bool {
	for _, validSignal := range VALID_KILL_SIGNALS {
		if value.SignalStruct.Signal == validSignal{
			return true
		}
	}
	return false
}

func parseKillsContainerFlag(killsContainer string) (bool, error) {

	upper := strings.ToUpper(killsContainer)
	//accepted value  YES or NO
	if upper == "YES" {
		return true, nil
	}
	if upper == "NO" {
		return false, nil
	}
	// else
	fmt.Println("Error incoming..")
	return false, fmt.Errorf("Kills Container Flag must be set to either YES or NO, received: '%s'", killsContainer)
}


// implementing interface
func (value sendSignal) target()  eventTarget  { return value.ParsedReplicas }
func (value stop) target()        eventTarget  { return value.ParsedReplicas }
func (value start) target()		  eventTarget { return value.ParsedReplicas }
func (value customFault) target() eventTarget { return value.ParsedReplicas }

func (value *stop) defaults() {}
func (value *start) defaults() {}
func (value *customFault) defaults() {
	value.Custom.Executable = "/bin/sh"
	value.Custom.FaultFileFolder = "/usr/lib/faultsee/"
	value.Custom.FaultScriptArguments = make([]string, 0)
	value.Custom.ExecutableArguments = make([]string, 0)
}

func (value *sendSignal) buildKill(raw interface{}) error {
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("ParseFault: Error Building KILL. Error: %v. Input: %s", err, raw)
		return err2
	}
	parsedReplicas, err3 := parseReplicas(value.RawReplicas)
	if err3 != nil {
		err4 := fmt.Errorf("Parse Target: Error Building KILL. Error: %v", err3)
		return err4

	}
	value.ParsedReplicas = parsedReplicas
	value.SignalStruct.Signal = "SIGKILL"
	value.SignalStruct.KillsContainer = true
	debug.ParseChurnDebug(action_spaces, "KILL", value)
	return nil
}
func (value *sendSignal) buildSignal(raw interface{}) error {
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("ParseFault: Error Building SIGNAL. Error: %v. Input: %s", err, raw)
		return err2
	}
	parsedReplicas, err3 := parseReplicas(value.RawReplicas)
	if err3 != nil {
		err4 := fmt.Errorf("Parse Target: Error Building SIGNAL. %v. ", err3)
		return err4

	}
	value.ParsedReplicas = parsedReplicas

	value.SignalStruct.Signal = strings.ToUpper(value.SignalStruct.Signal)
	if valid := value.validateSignal() ; !valid {
		err3 := fmt.Errorf("Invalid Signal: %s", value.SignalStruct.Signal)
		err2 := fmt.Errorf("ParseFault: Error Building %s. Error: %v. Input: %s", typeof(value), err3, raw)
		return err2
	}
	killsContainer, err5 := parseKillsContainerFlag(value.SignalStruct.RawKillsContainer)
	if err5 != nil {
		err6 := fmt.Errorf("ParseFault: Error Building SIGNAL. Error: %v. Input: %s", err5, raw)
		return err6
	}
	value.SignalStruct.KillsContainer = killsContainer

	debug.ParseChurnDebug(action_spaces, typeof(value), value)
	return nil
}


func (value *stop) build(raw interface{}) error {
	value.defaults()
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("ParseFault: Error Building %s. Error: %v. Input: %s", typeof(value), err, raw)
		return err2
	}
	parsedReplicas, err3 := parseReplicas(value.RawReplicas)
	if err3 != nil {
		err4 := fmt.Errorf("Parse Target: Error Building %s. %v", typeof(value), err3)
		return err4
	}
	value.ParsedReplicas = parsedReplicas
	debug.ParseChurnDebug(action_spaces, typeof(value), value)
	return nil
}
func (value *start) build(raw interface{}) error {
	value.defaults()
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("ParseFault: Error Building %s. Error: %v. Input: %s", typeof(value), err, raw)
		return err2
	}
	parsedReplicas, err3 := parseReplicas(value.RawReplicas)
	if err3 != nil {
		err4 := fmt.Errorf("Parse Target: Error Building %s. Error: %v. Input: %s", typeof(value), err3, raw)
		return err4
	}
	value.ParsedReplicas = parsedReplicas
	debug.ParseChurnDebug(action_spaces, typeof(value), value)
	return nil
}
func (value *customFault) build(raw interface{}) error {
	value.defaults()
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("ParseFault: Error Building %s. Error: %v. Input: %s", typeof(value), err, raw)
		return err2
	}
	parsedReplicas, err3 := parseReplicas(value.RawReplicas)
	if err3 != nil {
		err4 := fmt.Errorf("Parse Target: Error Building %s. %v", typeof(value), err3)
		return err4
	}
	value.ParsedReplicas = parsedReplicas

	killsContainer, err5 := parseKillsContainerFlag(value.Custom.RawKillsContainer)
	if err5 != nil {
		err6 := fmt.Errorf("ParseFault: Error Building %s. Error: %v. Input: %s",typeof(value), err5, raw)
		return err6
	}
	value.Custom.KillsContainer = killsContainer

	debug.ParseChurnDebug(action_spaces, typeof(value), value)
	return nil
}

// internally CPU is a custom Fault, with preset values
func (value *customFault) buildCPU(raw interface{}) error {
	type cpuFaultAux struct {
		RawReplicas          map[string]interface{} `yaml:"target"`
		ParsedReplicas       eventTarget    		`yaml:"-"`
		CPU struct{
			Duration int
		}
	}

	auxBuilder := cpuFaultAux{}

	value.defaults()
	err := ParseIntoCorrectStruct(raw, &auxBuilder)
	if err != nil {
		err2 := fmt.Errorf("ParseFault: Error Building CPU. Error: %v. Input: %s", err, raw)
		return err2
	}
	parsedReplicas, err3 := parseReplicas(auxBuilder.RawReplicas)
	if err3 != nil {
		err4 := fmt.Errorf("Parse Target: Error Building CPU. %v",  err3)
		return err4
	}
	value.ParsedReplicas = parsedReplicas

	// CPU values
	value.Custom.KillsContainer = false
	value.Custom.FaultFileName = "waste_cpu"
	//value.FaultFileFolder -> default
	//value.Executable  -> default
	//value.ExecutableArguments  -> default
	if auxBuilder.CPU.Duration <= 0 {
		// err
		err5 := fmt.Errorf("CPU duration must be set and bigger than 0. Input: %s", raw)
		return err5

	}

	value.Custom.FaultScriptArguments = []string{strconv.Itoa(auxBuilder.CPU.Duration)}

	debug.ParseChurnDebug(action_spaces, typeof(value), value)
	return nil
}

func (value sendSignal) createExecutableEvent(currentReplicasMap *map[string]serviceReplicasHolder, translator TranslateServiceSlot, serviceName string, time int) (moments []executableEvent, err error) {
	if beforeEventReplicasHolder, ok := (*currentReplicasMap)[serviceName]; ok {
		printBeforeAction(&beforeEventReplicasHolder, serviceName)

		var slotsToApply []int
		var err2 error
		var afterEventHolder serviceReplicasHolder
		if value.SignalStruct.KillsContainer {
			afterEventHolder, slotsToApply, err2 = value.target().calculateKill(beforeEventReplicasHolder)
			if err2 != nil {
				err = fmt.Errorf("CreateServiceEvent: Time «%d» - Type: «%s» - Service: «%s» Error: «%v»", time, typeof(value), serviceName, err2)
				return
			}
		} else {
			afterEventHolder = beforeEventReplicasHolder
			slotsToApply, err2 = value.target().calculateIdle(beforeEventReplicasHolder)
			if err2 != nil {
				err = fmt.Errorf("CreateServiceEvent: Time «%d» - Type: «%s» - Service: «%s» Error: «%v»", time, typeof(value), serviceName, err2)
				return
			}
		}
		(*currentReplicasMap)[serviceName] = afterEventHolder

		moments = make([]executableEvent, 0, len(slotsToApply))

		for _, internalSlot := range slotsToApply {
			executableMomentStruct := executableEventStruct{
				Time: time,
				ProcessedInThisNode:false,
				Id: ActionsIdManager.NextAvailableID(),
			}
			injector := sendSignalWorker{
				Signal: value.SignalStruct.Signal,
			}
			slot, errTranslator := translator(internalSlot)
			// abort operation if there is an  error with the translation
			if errTranslator != nil {
				err = errTranslator
				return
			}
			moment := NewExecutableContainerMoment( executableMomentStruct, injector , serviceName, slot)
			moments = append(moments, moment)
		}
		printAction(value.String(), time)
		printAfterAction(&afterEventHolder, serviceName)	} else {
		err = fmt.Errorf("CreateServiceEvent: Time «%d» - Type: «%s» - Service «%s» not specified in start values ", time, typeof(value), serviceName)
		return
	}
	return
}
func (value stop) createExecutableEvent(currentReplicasMap *map[string]serviceReplicasHolder, translator TranslateServiceSlot, serviceName string, time int) (moments []executableEvent, err error) {
	if beforeEventReplicasHolder, ok := (*currentReplicasMap)[serviceName]; ok {
		printBeforeAction(&beforeEventReplicasHolder, serviceName)
		afterEventHolder, slotsToApply, err2 := value.target().calculateKill(beforeEventReplicasHolder)
		if err2 != nil {
			err = fmt.Errorf("CreateServiceEvent: Time «%d» - Type: «%s» - Service: «%s» Error: «%v»", time, typeof(value), serviceName, err2)
			return
		}
		(*currentReplicasMap)[serviceName] = afterEventHolder

		moments = make([]executableEvent, 0, len(slotsToApply))

		for _, internalSlot := range slotsToApply {
			executableMomentStruct := executableEventStruct{
				Time: time,
				ProcessedInThisNode:false,
				Id: ActionsIdManager.NextAvailableID(),
			}
			injector := stopContainerWorker{}
			slot, errTranslator := translator(internalSlot)
			// abort operation if there is an  error with the translation
			if errTranslator != nil {
				err = errTranslator
				return
			}
			moment := NewExecutableContainerMoment( executableMomentStruct, injector , serviceName, slot)
			moments = append(moments, moment)
		}
		printAction(value.String(), time)
		printAfterAction(&afterEventHolder, serviceName)
	} else {
		err = fmt.Errorf("CreateServiceEvent: Time «%d» - Type: «%s» - Service «%s» not specified in start values ", time, typeof(value), serviceName)
		return
	}
	return
}

func (value start) createExecutableEvent(currentReplicasMap *map[string]serviceReplicasHolder, translator TranslateServiceSlot, serviceName string, time int) (moments []executableEvent, err error) {
	if beforeEventReplicasHolder, ok := (*currentReplicasMap)[serviceName]; ok {
		printBeforeAction(&beforeEventReplicasHolder, serviceName)
		afterEventHolder, err2 := value.target().calculateAdd(beforeEventReplicasHolder)
		if err2 != nil {
			err = fmt.Errorf("CreateServiceEvent: Time «%d» - Type: «%s» - Service: «%s» Error: «%v»", time, typeof(value), serviceName, err2)
			return
		}
		(*currentReplicasMap)[serviceName] = afterEventHolder


		moments = make([]executableEvent, 0, 1)

		markStartMoment := &StartContainersMoment {
			numberContainers: value.target().NumberAffected(beforeEventReplicasHolder),
			serviceName: serviceName,
			executableEventStruct: executableEventStruct{
				Time: time,
				ProcessedInThisNode:false,
				Id: ActionsIdManager.NextAvailableID(),
			},
		}

		moments = append(moments, markStartMoment)
		printAction(value.String(), time)
		printAfterAction(&afterEventHolder, serviceName)
	} else {
		err = fmt.Errorf("CreateServiceEvent: Time «%d» - Type: «%s» - Service «%s» not specified in start values ", time, typeof(value), serviceName)
		return
	}
	return
}

func (value customFault) createExecutableEvent(currentReplicasMap *map[string]serviceReplicasHolder, translator TranslateServiceSlot, serviceName string, time int) (moments []executableEvent, err error) {
	if beforeEventReplicasHolder, ok := (*currentReplicasMap)[serviceName]; ok {
		printBeforeAction(&beforeEventReplicasHolder, serviceName)
		var slotsToApply []int
		var err2 error
		var afterEventHolder serviceReplicasHolder
		if value.Custom.KillsContainer {
			afterEventHolder, slotsToApply, err2 = value.target().calculateKill(beforeEventReplicasHolder)
			if err2 != nil {
				err = fmt.Errorf("CreateServiceEvent: Time «%d» - Type: «%s» - Service: «%s» Error: «%v»", time, typeof(value), serviceName, err2)
				return
			}
		} else {
			afterEventHolder = beforeEventReplicasHolder
			slotsToApply, err2 = value.target().calculateIdle(beforeEventReplicasHolder)
			if err2 != nil {
				err = fmt.Errorf("CreateServiceEvent: Time «%d» - Type: «%s» - Service: «%s» Error: «%v»", time, typeof(value), serviceName, err2)
				return
			}
		}
		(*currentReplicasMap)[serviceName] = afterEventHolder

		moments = make([]executableEvent, 0, len(slotsToApply))
		faultDetais := faults.FaultDetails{
			FaultScriptFileName:     value.Custom.FaultFileName,
			FaultScriptFolder:       value.Custom.FaultFileFolder,
			Executable:          value.Custom.Executable,
			ExecutableArguments:    value.Custom.ExecutableArguments,
			FaultScriptArguments: value.Custom.FaultScriptArguments,
		}
		for _, internalSlot := range slotsToApply {
			executableMomentStruct := executableEventStruct{
					Time: time,
					ProcessedInThisNode:false,
					Id: ActionsIdManager.NextAvailableID(),
			}
			injector := injectFaultWorker{
				Details: faultDetais,
			}
			slot, errTranslator := translator(internalSlot)
			// abort operation if there is an  error with the translation
			if errTranslator != nil {
				err = errTranslator
				return
			}
			moment := NewExecutableContainerMoment( executableMomentStruct, injector , serviceName, slot)
			moments = append(moments, moment)
		}
		printAction(value.String(), time)
		printAfterAction(&afterEventHolder, serviceName)
	} else {
		err = fmt.Errorf("CreateServiceEvent: Time «%d» - Type: «%s» - Service «%s» not specified in start values ", time, typeof(value), serviceName)
		return
	}
	return
}



func buildEventsArray(auxServiceFaults map[string][](map[string]interface{})) (map[string][]RawServiceEvent, error) {
	finalFaultMap := make(map[string][]RawServiceEvent)


	for serviceName, actionsArray := range auxServiceFaults {
		// faultArray is array of faults
		debug.ParseChurnDebug(action_spaces, "Service", serviceName)
		var serviceFaults []RawServiceEvent
		for _, fault := range actionsArray {
			debug.ParseChurnDebug(action_spaces, "fault", fault)
			for faultType := range fault {
				switch faultType {
				case "start":
					var startAction start
					if err := startAction.build(fault[faultType]); err != nil {
						return nil, err
					}
					serviceFaults = append(serviceFaults, startAction)
				case "stop":
					var stopAction stop
					// just to make sure there are no errors
					if err := stopAction.build(fault[faultType]); err != nil {
						return nil, err
					}

					serviceFaults = append(serviceFaults, stopAction)
				case "fault":
					var faultBuilder map[string]interface{}
					errFaultBuilder := ParseIntoCorrectStruct(fault[faultType], &faultBuilder)
					if errFaultBuilder != nil {
						err2 := fmt.Errorf("ParseFault: Error Parsing Fault. Error: %v. Input: %s", errFaultBuilder , fault[faultType])
						return nil, err2
					}
					built := false
					loop:
						for key := range faultBuilder{
							cappitalLettersKey := strings.ToUpper(key)
							switch cappitalLettersKey {
								case "CPU":
									var cpuAction customFault
									if err := cpuAction.buildCPU(fault[faultType]); err != nil {
										return nil, err
									}
									serviceFaults = append(serviceFaults, cpuAction)
									built = true
									break loop
								case "CUSTOM":
									var custom customFault
									if err := custom.build(fault[faultType]); err != nil {
										return nil, err
									}
									serviceFaults = append(serviceFaults, custom)
									built = true
									break loop
								case "KILL":
									var killAction sendSignal
									if err := killAction.buildKill(fault[faultType]); err != nil {
										return nil, err
									}
									serviceFaults = append(serviceFaults, killAction)
									built = true
									break loop
								case "SIGNAL":
									var signalAction sendSignal
									if err := signalAction.buildSignal(fault[faultType]); err != nil {
										return nil, err
									}
									serviceFaults = append(serviceFaults, signalAction)
									built = true
									break loop
							}
						}
					if ! built {
						err := fmt.Errorf("ParseFaults: Could not build fault. Appears in service %s Input: %s", serviceName, fault)
						return nil, err
					}

				default:
					err := fmt.Errorf("ParseFaults: '%s' not support as fault type. Appears in service %s Input: %s", faultType, serviceName, fault)
					return nil, err
				}
			}
		}
		finalFaultMap[serviceName] = serviceFaults
	}
	return finalFaultMap, nil
}



// -------------- DEBUG Messages ----------------------------//
func printServicesMapStatus(replicasMap *map[string]serviceReplicasHolder, ) {
	for serviceName, replicas := range *replicasMap {
		messageToPrint := fmt.Sprintf("Service: %s\n" +
			"\tAlive: %v\n" +
			"\t Dead: %v\n",
			serviceName, replicas.holderAlive, replicas.holderDead)
		debug.StateService(messageToPrint)
	}
}

func printServiceStatus(holder *serviceReplicasHolder, serviceName string) {
	messageToPrint := fmt.Sprintf("Service: %s\n" +
		"\tAlive: %v\n" +
		"\t Dead: %v\n",
		serviceName, holder.holderAlive, holder.holderDead)
	debug.StateService(messageToPrint)
}

func printBeforeAction(beforeHolder *serviceReplicasHolder, serviceName string){
	debug.StateService("")
	debug.StateService("----------------------------------------------------------")
	debug.StateService("----------------------------------------------------------")
	debug.StateService("          -------------------------------------           ")
	printServiceStatus(beforeHolder, serviceName)
}
func printAction(action string, time int) {
	debug.StateService("          -------------------------------------           ")
	debug.StateService(fmt.Sprintf("Time: %d, %s", time, action))
	debug.StateService("          -------------------------------------           ")
}
func printAfterAction(afterHolder *serviceReplicasHolder, serviceName string) {
	printServiceStatus(afterHolder, serviceName)
	debug.StateService("          -------------------------------------           ")
	debug.StateService("----------------------------------------------------------")
	debug.StateService("----------------------------------------------------------")
	debug.StateService("")
}
// -------------- DEBUG Messages ----------------------------//
