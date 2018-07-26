package driver

import (
	"errors"
	"fmt"
	"log"
	"net"
	"strconv"

	"github.com/docker/go-plugins-helpers/ipam"
)

type Driver struct {
	addr      string
	allocator Allocator
}

func New(addr string) *Driver {
	d := &Driver{
		addr:      addr,
		allocator: Allocator{},
	}

	d.allocator.Init()
	return d
}

func (d *Driver) Run() {
	log.Println("IPAM server started on", d.addr)
	h := ipam.NewHandler(d)
	h.ServeTCP("lsdsuite-ipam", d.addr, "", nil)
}

// IPAM API

func (d *Driver) GetCapabilities() (*ipam.CapabilitiesResponse, error) {
	log.Println("IPAM: GetCapabilities")
	return &ipam.CapabilitiesResponse{
		RequiresMACAddress: false,
	}, nil
}

func (d *Driver) GetDefaultAddressSpaces() (*ipam.AddressSpacesResponse, error) {
	log.Println("IPAM: GetDefaultAddressSpaces")
	return &ipam.AddressSpacesResponse{
		LocalDefaultAddressSpace:  "LOCAL",
		GlobalDefaultAddressSpace: "GLOBAL",
	}, nil
}

func (d *Driver) RequestPool(r *ipam.RequestPoolRequest) (*ipam.RequestPoolResponse, error) {
	log.Printf("IPAM: RequestPool: %+v\n", r)

	// TODO: check & refuse IPv6 requests
	subnet := r.SubPool
	if subnet == "" {
		subnet = r.Pool
	}

	node := r.Options["lsdsuite-node-id"]
	if node == "" {
		return nil, errors.New("No lsdsuite-node-id specified")
	}

	nodeID, err := strconv.Atoi(node)
	if err != nil {
		return nil, errors.New(fmt.Sprintf("Can't parse lsdsuite-node-id: %v", err))
	}

	pool, err := d.allocator.TryAllocatePool(r.AddressSpace, nodeID, subnet)
	if err != nil {
		return nil, err
	}

	log.Printf("Pool: %s", pool.ID())
	return &ipam.RequestPoolResponse{PoolID: pool.ID(), Pool: pool.String()}, nil
}

func (d *Driver) ReleasePool(r *ipam.ReleasePoolRequest) error {
	log.Printf("IPAM: ReleasePool: %+v", r)
	return d.allocator.ReleasePool(r.PoolID)
}

func (d *Driver) RequestAddress(r *ipam.RequestAddressRequest) (*ipam.RequestAddressResponse, error) {
	log.Printf("IPAM: RequestAddress: %+v\n", r)
	pool, err := d.allocator.GetPool(r.PoolID)
	if err != nil {
		return nil, err
	}

	var ip net.IP

	if r.Options["RequestAddressType"] == "com.docker.network.gateway" && r.Address == "" {
		ip = pool.GetGateway()
		ip, err = pool.RequestIP(ip)
	} else if r.Address != "" {
		ip = net.ParseIP(r.Address)
		ip, err = pool.RequestIP(ip)
	} else {
		ip, err = pool.RequestNew()
	}

	if err != nil {
		return nil, err
	}

	log.Printf("IP: %v\n", ip)
	return &ipam.RequestAddressResponse{
		Address: pool.StringIP(ip),
	}, nil
}

func (d *Driver) ReleaseAddress(r *ipam.ReleaseAddressRequest) error {
	log.Printf("IPAM: ReleaseAddress: %+v\n", r)
	pool, err := d.allocator.GetPool(r.PoolID)
	if err != nil {
		return err
	}

	ip := net.ParseIP(r.Address)
	return pool.ReleaseIP(ip)
}
