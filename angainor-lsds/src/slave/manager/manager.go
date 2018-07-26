package manager

import (
	"compress/gzip"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"os"
	"path"
	"slave/utils/ntp_sync"
	"strings"
	"time"

	"slave/manager/commands"
	"slave/manager/events"
	"slave/manager/experiment"
	"slave/manager/faults"
	"slave/manager/host"
	"slave/manager/logs"
	"slave/manager/stats"

	"github.com/beevik/ntp"
	"github.com/docker/docker/api/types"
	"github.com/docker/engine/client"
)

// TODO: add chan direction in all declarations (e.g. New(out chan<- Entry))
// TODO: change Entry to Message

// SlavePort - port where slave receives information
const SlavePort = 7000
const LogDir = "/out/logs"
const LogSocket = "/out/logs.sock"
const CompressLogs = false

type Manager struct {
	Cli               *client.Client
	Version           string
	Channels          channels
	Hostname          string
	LogFile           *os.File
	LogWriter         io.WriteCloser
	ExperimentManager *experiment.Manager
	cancelRound       context.CancelFunc
}

type channels struct {
	Output           chan string
	Logs             chan logs.Entry
	Stats            chan stats.Entry
	Events           chan events.Entry
	Host             chan host.Entry
	Commands         chan commands.Command
	ExperimentInput  chan string
	ExperimentOutput chan string
	Marks			 chan string
	// Experiment chan commands.Command
}

// ----------------------------------------------------------------

func New(cli *client.Client, version string) *Manager {
	return &Manager{
		Cli: cli,
		Version: version,
		Channels: channels{
			// TODO: what chans need to be buffered?
			// If the buffer values are too low, we risk deadlocks
			Output:           make(chan string, 1),
			Logs:             make(chan logs.Entry, 1),
			Stats:            make(chan stats.Entry, 1),
			Events:           make(chan events.Entry, 1),
			Host:             make(chan host.Entry, 1),
			Commands:         make(chan commands.Command, 1),
			ExperimentInput:  make(chan string, 1),
			ExperimentOutput: make(chan string, 1),
			Marks:			  make(chan string, 1),
			// Experiment: make(chan commands.Command, 1),
		},
	}
}

// ----------------------------------------------------------------

func (m *Manager) Run() {
	log.Println("START: MANAGER")

	os.MkdirAll(LogDir, os.ModePerm)

	if err := m.setLogFile(""); err != nil {
		log.Fatalf("FATAL: OUT: can't open '%s/default.log': %v", LogDir, err)
	}

	hostname, err := os.Hostname()
	if err != nil {
		log.Fatalf("FATAL: MANAGER: can't get hostname\n")
	}
	m.Hostname = hostname

	go commands.New(SlavePort, m.Channels.Commands).Run()
	go events.New(events.Options{}, m.Cli, m.Channels.Events).Run()
	go logs.New(LogSocket, m.Channels.Logs).Run()
	go host.New(1*time.Second, m.Channels.Host).Run()
	m.ExperimentManager = experiment.New(m.Cli, m.Channels.ExperimentInput, m.Channels.ExperimentOutput, m.Channels.Marks, "docker-swarm")

	go m.dispatch()

	for line := range m.Channels.Output {
		m.log(line)
	}
}

func (m *Manager) dispatch() {
	for {
		select {
		case cmd := <-m.Channels.Commands:
			go m.handle(cmd)

		case host := <-m.Channels.Host:
			v, _ := json.Marshal(host)
			m.Channels.Output <- fmt.Sprintf("%v [HOST]\t%s\t%s",
				time.Now().Format(time.RFC3339Nano),
				m.Hostname,
				string(v))

		case stats := <-m.Channels.Stats:
			v, _ := json.Marshal(stats.Stats)
			m.Channels.Output <- fmt.Sprintf("%v [STATS]\t%s\t%s",
				stats.Stats.Read.UTC().Format(time.RFC3339Nano),
				stats.ID,
				string(v))

		case event := <-m.Channels.Events:
			m.ExperimentManager.ParseDockerEvent(event)
			if event.Type != "container" {
				// TODO: do we need these events?
				// Let's keep them for now
				// break
			}
			// else {
			// 	idented, _ := json.MarshalIndent(event, "", "    ")
			// 	log.Printf("[EVENT]\n%s", string(idented))
			// }

			if event.Type == "container" {
				if event.Status == "start" {
					// Only collect stats for marked containers
					if _, ok := event.Actor.Attributes["org.lsdsuite.stats"]; ok {
						// A new container appeared
						go stats.New(event.Actor.ID, m.Cli, m.Channels.Stats).Run()
					}
					// if value, ok := event.Actor.Attributes["com.docker.swarm.task.name"]; ok {
					// 	log.Printf("[DOCKER] Start %s", value)
					// 	idented, _ := json.MarshalIndent(event, "", "    ")
					// 	log.Printf("[EVENT] Start\n%s", string(idented))
					// } else {
					// 	idented, _ := json.MarshalIndent(event, "", "    ")
					// 	log.Printf("[EVENT] Start\n%s", string(idented))
					// }
				}
				// if event.Status == "die" {
				// 	if value, ok := event.Actor.Attributes["com.docker.swarm.task.name"]; ok {
				// 		log.Printf("[DOCKER] Die %s", value)
				// 		idented, _ := json.MarshalIndent(event, "", "    ")
				// 		log.Printf("[EVENT] DIE\n%s", string(idented))
				// 	} else {
				// 		idented, _ := json.MarshalIndent(event, "", "    ")
				// 		log.Printf("[EVENT] DIE\n%s", string(idented))
				// 	}
				// }
			}

			v, _ := json.Marshal(event)
			m.Channels.Output <- fmt.Sprintf("%v [EVENT]\t%s\t%s",
				time.Unix(0, event.TimeNano).Format(time.RFC3339Nano),
				event.Actor.ID,
				string(v))

		case logs := <-m.Channels.Logs:
			m.Channels.Output <- fmt.Sprintf("%v [LOG]\t%s\t%s",
				logs.Time.UTC().Format(time.RFC3339Nano),
				logs.ID,
				logs.Message)

		case logMessage := <-m.Channels.ExperimentOutput:
			m.Channels.Output <- fmt.Sprintf("%v [experimentLOG]\t%s",
				time.Now().Format(time.RFC3339Nano),
				logMessage)

		case markMessage := <-m.Channels.Marks:
			m.Channels.Output <- fmt.Sprintf("%v [MARK]\t%s\t%s",
				time.Now().Format(time.RFC3339Nano),
				m.Hostname,
				markMessage)

		}
	}
}

func (m *Manager) setLogFile(file string) error {
	if file == "" {
		file = "default.log"
	}

	os.MkdirAll(LogDir, os.ModePerm)
	file = path.Join(LogDir, file)

	// Check if file is writable
	f, err := os.OpenFile(file, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0666)
	if err != nil {
		return err
	}

	if _, err = f.Write([]byte{}); err != nil {
		f.Close()
		return err
	}

	var w io.WriteCloser
	if CompressLogs {
		w, err = gzip.NewWriterLevel(f, gzip.DefaultCompression)
		if err != nil {
			f.Close()
			return err
		}
	} else {
		w = f
	}

	if m.LogWriter != nil {
		m.LogWriter.Close()
	}

	if m.LogFile != nil {
		m.LogFile.Close()
	}

	m.LogFile = f
	m.LogWriter = w

	return nil
}

func (m *Manager) log(line string) {
	if m.LogWriter == nil {
		log.Printf("ERROR: OUT: LogWriter is nil")
	}

	if _, err := m.LogWriter.Write([]byte(line + "\n")); err != nil {
		log.Printf("ERROR: OUT: can't write to log file: %v", err)
	}
}

func (m *Manager) handle(cmd commands.Command) {
	log.Printf("CMD: %+v\n", cmd)
	switch cmd.Command {
	case "status":
		cmd.Response <- resp("ok", m.Hostname)

	case "slave_version":
		cmd.Response <- resp("ok", m.Version)

	case "faults_hash":
		faultsPath := cmd.MapStringParams["path"]
		if faultsPath == "" {
			cmd.Response <- resp("err", "params.path required")
			break
		}
		fmt.Println("Request to MD5", faultsPath)
		hash, err := faults.CalculateMD5(faultsPath)
		if err != nil {
			cmd.Response <- resp("err", err.Error())
		}
		cmd.Response <- resp("ok", hash)

	case "ntp_sync":
		ntpSyncImage := cmd.MapStringParams["docker_image"]
		if ntpSyncImage  == "" {
			log.Println("ERROR: params.docker_image required for NTP sync operation")
			cmd.Response <- resp("err", "params.docker_image required for NTP sync operation")
			break
		}
		err := ntp_sync.LaunchContainer(m.Cli, ntpSyncImage)
		if err != nil {
			errorMsg := err.Error()
			log.Println("ERROR: ", errorMsg)
			cmd.Response <- resp("err", errorMsg)
		}
		cmd.Response <- resp("ok", "ntp sync container started")

	case "ntp_offset":
		// calculates the average offset, out of 5 tries
		sum := 0.0
		fails := 0
		success := 0.0

		for  ; success < 1.0 && fails < 5;  {
			time.Sleep(100 * time.Millisecond)
			var ntpTime *ntp.Response
			var err error
			ntpTime, err = ntp.Query("pool.ntp.org")
			if err != nil {
				time.Sleep(100 * time.Millisecond)
				fmt.Println("ERROR1: ", err)
				fails += 1
			} else {
				err := ntpTime.Validate()
				if err != nil {
					time.Sleep(100 * time.Millisecond)
					fmt.Println("ERROR2: ", err)

					fails += 1
				} else {
					success += 1.0
					log.Println("NTP Offset: ", ntpTime.ClockOffset.Seconds(), " seconds")
					sum = sum + ntpTime.ClockOffset.Seconds()
				}
			}
		}
		if fails == 5 {
			fmt.Println("There was an error")
			cmd.Response <- resp("err", "Failed To retrieve NTP from server more than 5 times")

		} else {

			stringNumber := fmt.Sprintf("%.5f", (1000*sum)/success )
			cmd.Response <- resp("ok", stringNumber)
		}

	case "log": // Switch logging output to `params.file` ("default.log" if empty)
		file := cmd.MapStringParams["file"]
		if err := m.setLogFile(file); err != nil {
			cmd.Response <- resp("err", err.Error())
			return
		}

		cmd.Response <- resp("ok", "")
		log.Printf("OUT: '%s'", file)

	// Kill/pause/unpause containers `params.id` (comma-separated list of IDs) with signal `params.signal`
	case "kill", "pause", "unpause":
		id := cmd.MapStringParams["id"]
		if id == "" {
			cmd.Response <- resp("err", "params.id required")
			break
		}

		ids := strings.Split(id, ",")
		_, err := m.containerKillPauseUnpause(cmd.Command, cmd.MapStringParams["signal"], ids)

		if err != nil {
			cmd.Response <- resp("err", err.Error())
			break
		}

		cmd.Response <- resp("ok", "")
		// cmd.Response <- resp("ok", strings.Join(ok, ","))

	case "custom":
		id := cmd.MapStringParams["id"]
		if id == "" {
			cmd.Response <- resp("err", "params.id required")
			break
		}
		// faultName := cmd.Params["fault_file_name"]
		// if faultName == "" {
		// 	cmd.Response <- resp("err", "params.fault_file_name required")
		// 	break
		// }
		faultFileName := cmd.MapStringParams["fault_file_name"]
		faultFileFolder := cmd.MapStringParams["fault_file_folder"]
		executable := cmd.MapStringParams["executable"]
		executableArguments := cmd.MapArrayStringParams["executable_arguments"]    //arrays
		faultScriptArguments := cmd.MapArrayStringParams["fault_script_arguments"] //arrays

		fmt.Println("fault_file_name: ", faultFileName)
		fmt.Println("fault_file_folder: ", faultFileFolder)
		fmt.Println("executable: ", executable)
		fmt.Println("executable_arguments: ", executableArguments)
		fmt.Println("fault_script_arguments: ", faultScriptArguments)

		ids := strings.Split(id, ",")
		faultDetails := faults.FaultDetails{
			// Seconds:             25, // FIXME Required?
			FaultScriptFileName:     faultFileName,
			FaultScriptFolder:       faultFileFolder,
			FaultScriptArguments:    faultScriptArguments,
			Executable:              executable,
			ExecutableArguments:     executableArguments,
		}
		err := faults.InjectFault(m.Cli, ids, faultDetails)
		if err != nil {
			cmd.Response <- resp("err", err.Error())
			break
		}
		cmd.Response <- resp("ok", "")

	case "pull": // Pull image `params.image`
		image := cmd.MapStringParams["image"]
		if image == "" {
			cmd.Response <- resp("err", "params.image required")
			break
		}

		// TODO: context???
		// TODO: ImagePullOptions?
		rc, err := m.Cli.ImagePull(context.Background(), image, types.ImagePullOptions{})
		if err != nil {
			cmd.Response <- resp("err", err.Error())
			break
		}

		// The output isn't important for lsdsuite-master, but we consume it to
		// make sure the operation has finished
		body, err := ioutil.ReadAll(rc)
		if err != nil {
			cmd.Response <- resp("err", err.Error())
			break
		}

		fmt.Println("Image pull result:", string(body))
		cmd.Response <- resp("ok", "")

	case "mark":
		msg := cmd.MapStringParams["msg"]
		if msg == "" {
			cmd.Response <- resp("err", "params.msg required")
			break
		}

		m.Channels.Marks <- fmt.Sprintf("%s", msg)

		cmd.Response <- resp("ok", "")

	case "processed_moments":
		// Returns the experiment processed moments
		// TODO FIXME validate run exists
		// TODO validate ExperimentReady
		// TODO check if experiment is running
		eventsJSON := m.ExperimentManager.GetProcessedEvents()
		cmd.Response <- resp("ok", eventsJSON)

	case "restart_round":
		// TODO FIXME validate run exists
		// TODO validate ExperimentReady
		// TODO check if experiment is running
		msg := "Restart Round in preparation for next one"
		m.Channels.Output <- fmt.Sprintf("%v [ROUND]\t%s\t%s",
			time.Now().Format(time.RFC3339Nano),
			m.Hostname,
			msg)

		m.ExperimentManager.ResetRound()

		cmd.Response <- resp("ok", msg)

	case "start_run":
		// TODO FIXME validate run exists
		// TODO validate ExperimentReady
		// TODO check if experiment is running
		msg := "Start Run"
		m.Channels.Output <- fmt.Sprintf("%v [START-RUN]\t%s\t%s",
			time.Now().Format(time.RFC3339Nano),
			m.Hostname,
			msg)

		go m.ExperimentManager.PlayRun(nil, time.Now())

		cmd.Response <- resp("ok", "")

	case "cancel_run":
		if m.cancelRound == nil {
			cmd.Response <- resp("err", "No cancel function stored in manager. The experiment is out of control. Please consider turning restarting the cluster")
			break
		}
		m.cancelRound()
		log.Println("Round Cancelled")
		cmd.Response <- resp("ok", "Round cancelled")

	case "start_run_at":
		// TODO FIXME validate run exists
		// TODO validate ExperimentReady
		// TODO check if experiment is running
		datetime := cmd.MapStringParams["datetime"]
		if datetime == "" {
			cmd.Response <- resp("err", "params.datetime required")
			break
		}
		startMoment, err := time.Parse(time.RFC3339, datetime)

		if err != nil {
			cmd.Response <- resp("err", "Failed to parse start round moment")
			break
		}
		
		if time.Now().After(startMoment) {
			cmd.Response <- resp("err", "Start Experiment Moment expired")
			break
		}



		m.Channels.Output <- fmt.Sprintf("%v [PLANNED]\t%s\t%s %v",
			time.Now().Format(time.RFC3339Nano),
			m.Hostname,
			"Start experiment @",
			startMoment.Format(time.RFC3339))

		log.Printf("%v [PLANNED]\tStart Round @ %v\n", time.Now().Format(time.RFC3339Nano), startMoment.Format(time.RFC3339))


		ctx, cancel := context.WithCancel(context.Background())

		m.cancelRound = cancel

		go m.ExperimentManager.PlayRun(ctx, startMoment)

		cmd.Response <- resp("ok", "plan to start OK")


	case "start_dry_run":
		// TODO FIXME validate run exists
		msg := "Start DRY Run"
		m.Channels.Output <- fmt.Sprintf("%v [START-DRY-RUN]\t%s\t%s",
			time.Now().Format(time.RFC3339Nano),
			m.Hostname,
			msg)

		go m.ExperimentManager.DryRun()

		cmd.Response <- resp("ok", "")

	case "churn_string":
		churnString := cmd.MapStringParams["churn_string"]
		if churnString == "" {
			cmd.Response <- resp("err", "params.churn_string required")
			break
		}

		err := m.ExperimentManager.PrepareExperiment(churnString)
		if err != nil {
			log.Printf("PARSE_CHURN: ERROR %+v\n", err)
			cmd.Response <- resp("err", fmt.Sprint("While preparing experiment there was an error:", err))
			break
		}
		log.Printf("PARSE_CHURN: OK\n")
		cmd.Response <- resp("ok", "")

	case "ipam":
		name := "faultsee-ipam"
		id := cmd.MapStringParams["id"]
		if id == "" {
			cmd.Response <- resp("err", "params.id required")
			break
		}

		image := cmd.MapStringParams["image"]
		if image == "" {
			cmd.Response <- resp("err", "params.image required")
			break
		}

		port := cmd.MapStringParams["port"]
		if port == "" {
			cmd.Response <- resp("err", "params.port required")
			break
		}

		// First, remove the plugin if it is already installed
		// TODO: context???
		// We don't care about the return value (error), it just means that the plugin wasn't installed
		m.Cli.PluginRemove(context.Background(), name, types.PluginRemoveOptions{Force: true})

		opt := types.PluginInstallOptions{
			Disabled:             false,
			AcceptAllPermissions: true,
			RemoteRef:            image,
			Args: []string{
				fmt.Sprintf("REMOTE=127.0.0.1:%s", port),
				fmt.Sprintf("NODE_ID=%s", id),
			},
		}

		log.Printf("OPT = %+v", opt)

		// TODO: context???
		rc, err := m.Cli.PluginInstall(context.Background(), name, opt)
		if err != nil {
			log.Printf("err %+v", err.Error())
			cmd.Response <- resp("err", err.Error())
			break
		}

		// The output isn't important for lsdsuite-master, but we consume it to
		// make sure the operation has finished
		body, err := ioutil.ReadAll(rc)
		if err != nil {
			log.Printf("err %+v", err.Error())
			cmd.Response <- resp("err", err.Error())
			break
		}

		log.Println("Plugin install result: ", string(body))
		cmd.Response <- resp("ok", "")

	default:
		cmd.Response <- resp("err", fmt.Sprintf(`unknown command "%s"`, cmd.Command))
	}

}

type killResult struct {
	id  string
	err error
}

func (m *Manager) containerKillPauseUnpause(action string, signal string, ids []string) ([]string, error) {
	var f func(*client.Client, string, string, chan killResult)
	switch action {
	case "kill":
		f = containerKill

	case "pause":
		f = containerPause

	case "unpause":
		f = containerUnpause

	default:
		return nil, errors.New("Unsupported action: " + action)
	}

	res := make(chan killResult)

	// Start threads
	for _, id := range ids {
		go f(m.Cli, id, signal, res)
		time.Sleep(10 * time.Millisecond)
	}

	// Wait for threads to finish
	ok := make([]string, 0, len(ids))
	for _ = range ids {
		r := <-res
		if err := r.err; err != nil {
			log.Printf("Error handling %s: %v...", r.id, err)
		} else {
			ok = append(ok, r.id)
		}
	}

	return ok, nil
}

func containerKill(client *client.Client, id string, signal string, res chan killResult) {
	err := client.ContainerKill(context.Background(), id, signal)
	res <- killResult{id, err}
}

func containerPause(client *client.Client, id string, signal string, res chan killResult) {
	err := client.ContainerPause(context.Background(), id)
	res <- killResult{id, err}
}

func containerUnpause(client *client.Client, id string, signal string, res chan killResult) {
	err := client.ContainerUnpause(context.Background(), id)
	res <- killResult{id, err}
}

func resp(status string, message string) commands.Response {
	return commands.Response{status, message}
}
