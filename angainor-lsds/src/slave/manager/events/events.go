package events

import (
	"context"
	"log"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/api/types/events"
	"github.com/docker/engine/client"
)

type Manager struct {
	options Options
	cli     *client.Client
	out     chan Entry
}

type Options types.EventsOptions
type Entry events.Message

func New(options Options, cli *client.Client, out chan Entry) *Manager {
	return &Manager{
		options: options,
		cli:     cli,
		out:     out,
	}
}

func (m *Manager) Run() {
	options := types.EventsOptions(m.options)
	log.Printf("START: EVENT\n")

	for messages, errors := m.cli.Events(context.Background(), options); ; {
		select {
		case msg := <-messages:
			m.out <- Entry(msg)

		case err := <-errors:
			log.Fatalf("FATAL: EVENT: %v\n", err)
		}
	}
}
