package commands

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
)

type Manager struct {
	port uint
	out  chan Command
}

type Command struct {
	Command              string              `json:"command"`
	MapStringParams      map[string]string   `json:"MapStringParams"`
	MapArrayStringParams map[string][]string `json:"MapArrayStringParams"`
	Response             chan Response
}

type Response struct {
	Status  string `json:"status"`
	Message string `json:"msg,omitempty"`
}

func New(port uint, out chan Command) *Manager {
	return &Manager{
		port: port,
		out:  out,
	}
}

func (m *Manager) Run() {
	listener, err := net.Listen("tcp", fmt.Sprintf(":%d", m.port))
	if err != nil {
		log.Fatalf("FATAL: CMD: %v\n", err)
	}

	log.Printf("START: CMD: %d\n", m.port)
	defer listener.Close()

	for {
		conn, _ := listener.Accept()
		go m.handle(conn)
	}
}

func (m *Manager) handle(conn net.Conn) {
	defer conn.Close()

	respond := func(resp Response) {
		data, _ := json.Marshal(resp) // TODO: can an error even happen here?
		conn.Write(data)
		conn.Write([]byte{'\n'})
	}

	for decoder, cmd := json.NewDecoder(conn), (Command{}); ; {
		err := decoder.Decode(&cmd)
		if err == io.EOF {
			return
		}

		if err != nil {
			// TODO
			log.Printf("ERROR: CMD: JSON: %v\n", err)
			respond(Response{"err", err.Error()})
			return
		}

		cmd.Response = make(chan Response)
		m.out <- cmd
		// Wait for response and send it to client
		resp := <-cmd.Response
		respond(resp)

		// Return and thus close connection without handling further requests.
		// This simplifies master-side code, but isn't very elegant.
		return
	}
}
