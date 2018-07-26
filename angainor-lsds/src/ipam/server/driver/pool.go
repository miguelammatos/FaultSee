package driver

import (
	"encoding/binary"
	"errors"
	"fmt"
	"net"
	"time"
)

type Pool struct {
	space  string
	nodeID int
	subnet net.IPNet
	time   map[uint32]*time.Time
	next   uint32
}

func (p *Pool) Init() {
	p.time = make(map[uint32]*time.Time)
	p.next = p.firstIP()
}

func (p *Pool) String() string {
	return p.subnet.String()
}

func (p *Pool) ID() string {
	if p.space == "LOCAL" {
		return fmt.Sprintf("%s/%d|%v", p.space, p.nodeID, p)
	} else {
		return fmt.Sprintf("%s|%v", p.space, p)
	}
}

// Format IP to string with CIDR prefix length (as expected by Docker)
func (p *Pool) StringIP(ip net.IP) string {
	return fmt.Sprintf("%s/%d", ip, p.prefixSize())
}

func (p *Pool) prefixSize() int {
	s, _ := p.subnet.Mask.Size()
	return s
}

// First allocatable IP in pool (x.x.x.1)
func (p *Pool) firstIP() uint32 {
	ip := ipToInt(p.subnet.IP)
	// We don't want to allocate x.x.x.0 addresses (because they look strange)
	return ip + 1
}

// Last allocatable IP in pool
func (p *Pool) lastIP() uint32 {
	s := p.prefixSize()
	return p.firstIP() + uint32(1<<uint(32-s)) - 1
}

// Get next free IP
func (p *Pool) getNext() (uint32, error) {
	// Find the next never-allocated IP
	for i := p.next; i < p.lastIP(); i++ {
		_, ok := p.time[i]
		if !ok { // IP isn't in `time`, was never allocated
			p.next = i + 1
			return i, nil
		}
	}

	// Find free IP with oldest deallocation time
	found, ip, minTime := false, uint32(0), time.Now()
	for i := p.firstIP(); i < p.lastIP(); i++ {
		t := p.time[i]
		if t != nil && t.Before(minTime) {
			found, ip, minTime = true, i, *t
		}
	}

	if !found {
		return 0, errors.New("No free IP")
	}

	return ip, nil
}

// Tries to determine the pool's gateway IP by assuming it to be the first IP ending in .1
func (p *Pool) GetGateway() net.IP {
	return intToIp(p.firstIP())
}

// Request a new, free IP
func (p *Pool) RequestNew() (net.IP, error) {
	ip, err := p.getNext()
	if err != nil {
		return nil, err
	}

	p.time[ip] = nil // Mark IP as occupied
	return intToIp(ip), nil
}

// Request a specific IP
func (p *Pool) RequestIP(ip net.IP) (net.IP, error) {
	if !p.subnet.Contains(ip) {
		return nil, errors.New("IP out of range")
	}

	i := ipToInt(ip)
	t, ok := p.time[i]
	if ok && t == nil {
		return nil, errors.New("IP is occupied")
	}

	p.time[i] = nil
	return ip, nil
}

func (p *Pool) ReleaseIP(ip net.IP) error {
	if !p.subnet.Contains(ip) {
		// TODO: should we return an error?
		return nil
	}

	t := time.Now()
	p.time[ipToInt(ip)] = &t
	return nil
}

func (p *Pool) Overlaps(subnet net.IPNet) bool {
	// https://stackoverflow.com/questions/34729158/how-to-detect-if-two-golang-net-ipnet-objects-intersect
	return p.subnet.Contains(subnet.IP) || subnet.Contains(p.subnet.IP)
}

func (p *Pool) Conflicts(space string, nodeID int, subnet net.IPNet) bool {
	if p.space != space {
		return false
	}

	if space == "LOCAL" && p.nodeID != nodeID {
		return false
	}

	return p.Overlaps(subnet)
}

func ipToInt(ip net.IP) uint32 {
	return binary.BigEndian.Uint32(ip.To4())
}

func intToIp(int uint32) net.IP {
	ip := make([]byte, 4, 4)
	binary.BigEndian.PutUint32(ip, int)
	return ip
}
