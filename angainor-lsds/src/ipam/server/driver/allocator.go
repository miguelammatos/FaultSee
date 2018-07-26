package driver

import (
	"errors"
	"fmt"
	"log"
	"net"
)

type Allocator struct {
	pools map[string]*Pool
}

func (a *Allocator) Init() {
	a.pools = make(map[string]*Pool)
}

// Tries to allocate `subnet` on address space `space` by checking if any
// already-allocated pools on this space overlap subnet. If `subnet` is empty,
// tries to allocate a 10.x.0.0/16 subnet.
func (a *Allocator) TryAllocatePool(space string, nodeID int, subnet string) (*Pool, error) {
	log.Printf("TryAllocatePool: %s, %d, %s", space, nodeID, subnet)

	if space == "" {
		return nil, errors.New("AddressSpace must not be empty")
	}

	// If no pool is specified, get the first free 10.x.0.0/16 subnet.
	if subnet == "" {
		var err error = nil
		for i := 0; i <= 255; i++ {
			subnet = fmt.Sprintf("10.%d.0.0/16", i)
			pool, err := a.TryAllocatePool(space, nodeID, subnet)

			if err == nil {
				return pool, nil
			}
		}

		return nil, err
	} else {
		_, s, err := net.ParseCIDR(subnet)
		if err != nil {
			return nil, err
		}

		// Check if requested pool is free
		for _, pool := range a.pools {
			if pool.Conflicts(space, nodeID, *s) {
				return nil, errors.New(fmt.Sprintf("Pool %s conflicts %s @ %d", pool.ID(), subnet, nodeID))
			}
		}

		pool := &Pool{space: space, nodeID: nodeID, subnet: *s}
		pool.Init()
		a.pools[pool.ID()] = pool
		return pool, nil
	}
}

func (a *Allocator) ReleasePool(id string) error {
	log.Printf("ReleasePool: %s", id)
	delete(a.pools, id)
	return nil
}

func (a *Allocator) GetPool(id string) (*Pool, error) {
	pool, ok := a.pools[id]
	if !ok {
		return nil, errors.New("No such pool: " + id)
	}

	return pool, nil
}
