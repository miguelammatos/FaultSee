package logs

import (
	"bufio"
	"io"
	"log"
	"net"
	"os"
	"regexp"
	"time"
)

var LOG_REGEXP = regexp.MustCompile(`(?P<time>[-+.:T0-9Z]+) (?P<host>[^\s]+) (?P<id>\w+) \d+ \w+ - (?P<message>.*)`)

type Manager struct {
	socket string
	out    chan Entry
}

type Entry struct {
	Time    time.Time
	ID      string
	Message string
}

func New(socket string, out chan Entry) *Manager {
	return &Manager{
		socket: socket,
		out:    out,
	}
}

func (m *Manager) Run() {
	os.Remove(m.socket)
	listener, err := net.Listen("unix", m.socket)
	if err != nil {
		log.Fatalf("FATAL: LOG: %v\n", err)
	}

	log.Printf("START: LOG: '%s'\n", m.socket)
	defer os.Remove(m.socket)
	defer listener.Close()

	for {
		conn, _ := listener.Accept()
		go m.handle(conn)
	}
}

func (m *Manager) handle(conn net.Conn) {
	defer conn.Close()

	for reader := bufio.NewReader(conn); ; {
		msg, err := reader.ReadString('\n')
		if err == io.EOF {
			return
		}

		if err != nil {
			log.Printf("ERROR: LOG: %v\n", err)
			return
		}

		match := LOG_REGEXP.FindStringSubmatch(msg)
		if match == nil {
			// TODO
			log.Printf("ERROR: LOG: can't parse '%s'\n", msg)
			continue
		}

		t, err := time.Parse(time.RFC3339Nano, match[1])
		if err != nil {
			// TODO
			log.Printf("ERROR: LOG: can't parse time: %v\n", err)
			continue
		}

		m.out <- Entry{
			Time:    t,
			ID:      match[3],
			Message: match[4],
		}
	}
}
