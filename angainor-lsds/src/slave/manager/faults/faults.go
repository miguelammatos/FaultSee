package faults

import (
	"context"
	"fmt"
	"strings"

	"errors"
	"log"

	"github.com/docker/docker/api/types"
	"github.com/docker/engine/client"
)

const faultsFolderPath = "/usr/lib/faultsee/"

// FaultDetails - contains information used to Exec Order to run script that injects fault in a container
// @FaultScriptFileName - filename to read script
// @FaultScriptFolder - (OPTIONAL) Folder in which script is,
//					DEFAULT: "/usr/lib/faultsee/"
// 					Usefull to call commands from different folder
// @FaultScriptArguments - (OPTIONAL) parameters to append to the end of the script to run
// @Executable - executable program (e.g. /bin/sh)
// @Seconds - (OPTIONAL) run command for amount of seconds
// @ExecutableArguments - (OPTIONAL) Arguments for the executable
type FaultDetails struct {
	FaultScriptFileName      string
	FaultScriptFolder       string   //optional
	FaultScriptArguments    []string //optional
	Seconds             int      //optional //not supported maybe // FIXME Required?
	Executable          string   //optional
	ExecutableArguments []string //optional
}

func (value FaultDetails) String() string {
	return fmt.Sprint(value.Executable, " " ,value.ExecutableArguments, " ", value.FaultScriptFolder,  value.FaultScriptFileName, " ", value.FaultScriptArguments)
}

func inspectExecutionOrder(cli *client.Client, execID string) {
	execInspect, err := cli.ContainerExecInspect(context.Background(), execID)
	if err != nil {
		log.Println("Error" + err.Error())
		panic(err)
	}
	log.Println("execInspect.Running    : ", execInspect.Running)
}

func startExecutionOrder(cli *client.Client, execID string) error {
	config := types.ExecStartCheck{}
	err := cli.ContainerExecStart(context.Background(), execID, config)
	return err
}

func createExecutionOrder(cli *client.Client, containerID string, command []string) (string, error) {
	execConfiguration := types.ExecConfig{
		Detach: true,    // Execute in detach mode
		Cmd:    command, // Execution commands and args"
		// User:         "",
		// Privileged: false, // Is the container in privileged mode
		// Tty:        false, // Attach standard streams to a tty.
		// AttachStdin:  false, // Attach the standard input, makes possible user interaction
		// AttachStderr: true, // Attach the standard error
		// AttachStdout: true, // Attach the standard output
		// DetachKeys:   "",         // Escape keys for detach
		// Env: []string{}, // Environment variables
	}
	// create execution "order"
	response, err := cli.ContainerExecCreate(context.Background(), containerID, execConfiguration)
	if err != nil {
		log.Println("Error " + err.Error())
		return "", err
	}
	execID := response.ID
	if execID == "" {
		log.Println("Error execID empry")
		error := errors.New("Execution ID is empty")
		return execID, error
	}
	return execID, nil
}

// Transforms the Faultscipt information into an []string, that docker api requires
func createCommand(faultDetails FaultDetails) []string {
	// executable + arguments
	var strBuilder strings.Builder
	command := make([]string, 1+len(faultDetails.ExecutableArguments)+1+len(faultDetails.FaultScriptArguments))

	if faultDetails.FaultScriptFolder!= "" {
		// using a custom path
		strBuilder.WriteString(faultDetails.FaultScriptFolder)
	} else {
		strBuilder.WriteString(faultsFolderPath)
	}

	// append absolute folder path with command file name
	strBuilder.WriteString(faultDetails.FaultScriptFileName)
	filename := strBuilder.String()

	command[0] = faultDetails.Executable
	currentIndex := 1
	// append arguments
	for _, element := range faultDetails.ExecutableArguments {
		command[currentIndex] = element
		currentIndex++
	}
	command[currentIndex] = filename
	currentIndex++
	for _, element := range faultDetails.FaultScriptArguments {
		command[currentIndex] = element
		currentIndex++
	}

	return command

	// // read contents
	// fileContents, err := readCommandTemplateFromFile(filename)
	// if err == nil {
	// 	if faultScript.CommandParameters != "" {
	// 		// append parameters
	// 		strBuilder.Reset()
	// 		strBuilder.WriteString(fileContents)
	// 		strBuilder.WriteString(" ")
	// 		strBuilder.WriteString(faultScript.CommandParameters)
	// 		fileContents = strBuilder.String()
	// 	}
	// 	if faultScript.ExecutableArguments != "" {
	// 		commandSlice = []string{faultScript.Executable, faultScript.ExecutableArguments, fileContents}
	// 	} else {
	// 		commandSlice = []string{faultScript.Executable, fileContents}
	// 	}
	// }
	// return commandSlice, err
}

// func readCommandTemplateFromFile(filename string) (string, error) {
// 	bytesContent, err := ioutil.ReadFile(filename)
// 	if err != nil {
// 		return "", err
// 	}
//
// 	// convert content to 'string'
// 	command := string(bytesContent)
// 	return command, nil
// }

// func createWasteCPUCommand(numberSecondsWasted string) []string {
// 	wasteCPUCommand := `
// 	waste_cpu() {
// 		while true
// 		do
// 			echo "ola123" | sha256sum
// 		done
// 	}
// 	timeout_child () {
// 		trap -- "" SIGTERM
// 		child=$!
// 		timeout=$1
// 		(
// 			sleep $timeout
// 			kill $child
// 		) &
// 		wait $child
// 	}
// 	waste_cpu & timeout_child %s`
// 	commandFinal := fmt.Sprintf(wasteCPUCommand, numberSecondsWasted)
// 	command := []string{"sh", "-c", commandFinal}
// 	return command
// }

// WasteCPU is a function TODO Comment
// func WasteCPU(cli *client.Client, containerID string, numberSeconds string, errorsChannel chan error) {
// 	log.Printf("START: wasteCPU @ %s during %s seconds\n", containerID, numberSeconds)
//
// 	command := createWasteCPUCommand(numberSeconds)
// 	execID, err := createExecutionOrder(cli, containerID, command)
// 	if err != nil {
// 		log.Println("Error " + err.Error())
// 		errorsChannel <- err
// 		return
// 		// TODO handle error
// 	}
// 	err = startExecutionOrder(cli, execID)
// 	if err != nil {
// 		log.Println("Error " + err.Error())
// 		errorsChannel <- err
// 		return
// 	}
// 	errorsChannel <- nil
// 	return
// }

// InjectFaultOnContainer injects a fault in a single container
// @cli - is the docker API client
// @containerID - docker container identifier
func injectFaultOnContainer(cli *client.Client, containerID string, command []string) error {
	// log.Printf("START: StartCommand @ %s during %d seconds\n", containerID, faultScript.Seconds)
	execID, err := createExecutionOrder(cli, containerID, command)
	if err != nil {
		err2 := fmt.Errorf("Ignoring .. Error while creating execution order of command «%v» for container «%s» ERR: «%v»", command, containerID, err)
		log.Println("Error: %v...", err2)
		return err2
	}

	err = startExecutionOrder(cli, execID)
	if err != nil {
		err2 := fmt.Errorf("Ignoring .. Error while starting execution of command «%v» for container «%s» ERR: «%v»", command, containerID, err)
		log.Println("Error: %v...", err2)
		return err2
	}
	return nil
}

// InjectFaultOnContainer injects a fault in a single container
// @cli - is the docker API client
// @containerID - docker container identifier
func InjectFaultOnContainer(client *client.Client, containerID string, faultScript FaultDetails) (errorToReturn error) {
	command := createCommand(faultScript)
	err := injectFaultOnContainer(client, containerID, command)
	return err
}

// SendSignalToContainer sends a signal to a containerID
func SendSignalToContainer(client *client.Client, containerID string, signal string) error {
	log.Println("Sending signal %s to container %s", signal, containerID)
	err := client.ContainerKill(context.Background(), containerID, signal)
	if err != nil{
		fmt.Println("Error sending Siganl..", err)
	}
	return err
}

// InjectFault injects fault described in @faultScript on containers listed in @ids
func InjectFault(client *client.Client, ids []string, faultScript FaultDetails) (errorToReturn error) {
	res := make(chan error)
	errorToReturn = nil

	command := createCommand(faultScript)
	fmt.Println(command)
	// if err != nil {
	// 	log.Println("Error " + err.Error())
	// 	errorToReturn = err
	// 	return
	// }

	// Start threads
	for _, id := range ids {
		go injectFaultOnContainer(client, id, command) //FIXME: Currently ignoring errors..
	}

	// Wait for threads to finish
	// ok := make([]string, 0, len(ids))
	for _ = range ids {
		err := <-res
		if err != nil {
			log.Printf("Error: %v...", err)
		} else {
			errorToReturn = err
			// we got an error
		}
		// else {
		// 	ok = append(ok, r.id)
		// }
	}
	return errorToReturn
}
