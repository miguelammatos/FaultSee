package host

import (
	"log"
	"time"

	"github.com/shirou/gopsutil/cpu"
	"github.com/shirou/gopsutil/disk"
	"github.com/shirou/gopsutil/load"
	"github.com/shirou/gopsutil/mem"
	"github.com/shirou/gopsutil/net"
)

// File that reads HOST resource usage metrics

type Manager struct {
	interval time.Duration
	out      chan Entry
}

type Entry struct {
	CPU        map[string]cpu.TimesStat       `json:"cpu"`
	CPUPercent []float64                      `json:"cpuPercent"`
	Load       load.AvgStat                   `json:"load"`
	Mem        mem.VirtualMemoryStat          `json:"mem"`
	Disk       map[string]disk.IOCountersStat `json:"disk"`
	Net        map[string]net.IOCountersStat  `json:"net"`
}

func New(interval time.Duration, out chan Entry) *Manager {
	return &Manager{
		interval: interval,
		out:      out,
	}
}

func (m *Manager) Run() {
	log.Printf("START: HOST: %v\n", m.interval)

	for range time.Tick(m.interval) {
		stats, err := m.read()
		if err != nil {
			log.Fatalf("ERROR: HOST: %v\n", err)
		}

		m.out <- *stats
	}
}

func (m *Manager) read() (*Entry, error) {
	cpuStats, err := cpu.Times(true)
	if err != nil {
		return nil, err
	}

	cpuTotal, err := cpu.Times(false)
	if err != nil {
		return nil, err
	}

	cpuPercent, err := cpu.Percent(0, true)
	if err != nil {
		return nil, err
	}

	cpuPercentTotal, err := cpu.Percent(0, false)
	if err != nil {
		return nil, err
	}

	loadAvg, err := load.Avg()
	if err != nil {
		return nil, err
	}

	mem, err := mem.VirtualMemory()
	if err != nil {
		return nil, err
	}

	netStats, err := net.IOCounters(true)
	if err != nil {
		return nil, err
	}

	netTotal, err := net.IOCounters(false)
	if err != nil {
		return nil, err
	}

	disk, err := disk.IOCounters()
	if err != nil {
		return nil, err
	}

	cpu := make(map[string]cpu.TimesStat)
	for _, c := range append(cpuStats, cpuTotal...) {
		cpu[c.CPU] = c
	}

	net := make(map[string]net.IOCountersStat)
	for _, n := range append(netStats, netTotal...) {
		net[n.Name] = n
	}

	return &Entry{
		CPU:        cpu,
		CPUPercent: append(cpuPercentTotal, cpuPercent...),
		Load:       *loadAvg,
		Mem:        *mem,
		Disk:       disk,
		Net:        net,
	}, nil
}
