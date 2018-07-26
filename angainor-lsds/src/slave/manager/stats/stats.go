package stats

import (
	"context"
	"encoding/json"
	"io"
	"log"
	"time"

	"github.com/docker/docker/api/types"
	"github.com/docker/engine/client"
)

type Manager struct {
	id  string
	cli *client.Client
	out chan Entry
}

type Entry struct {
	ID    string
	Stats Stats
}

type Stats types.StatsJSON

func New(id string, cli *client.Client, out chan Entry) *Manager {
	return &Manager{
		id:  id,
		cli: cli,
		out: out,
	}
}

func (m *Manager) Run() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	stream, err := m.cli.ContainerStats(ctx, m.id, true)
	if err != nil {
		// TODO
		log.Printf("ERROR: stats[%s]: %v\n", m.id, err)
		return
	}
	defer stream.Body.Close()

	log.Printf("START: stats[%s]\n", m.id)
	defer log.Printf("STOP: stats[%s]\n", m.id)

	for stats := (Stats{}); ; {
		if err = json.NewDecoder(stream.Body).Decode(&stats); err != nil {
			if err == io.EOF {
				return
			}

			// Ignore parsing errors
			log.Printf("ERROR: stats[%s]: JSON: %v\n", m.id, err)
			return
		}

		// "zero" time indicates absence of data, which happens either when the container
		// hasn't started yet or was stopped. We ignore this
		if stats.Read == (time.Time{}) {
			continue
		}

		// TODO: compute CPU usage percent:
		// https://github.com/moby/moby/blob/18a771a761654e241ae8d1e85aa0c0a6164c5d27/integration-cli/docker_api_stats_test.go
		// And pre-digest stats into a more useful format (possibly same format as host stats)
		m.out <- Entry{
			ID:    m.id,
			Stats: stats,
		}
	}
}
