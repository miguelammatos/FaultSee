package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/docker/go-plugins-helpers/ipam"
)

/*

This is the part of lsdsuite-ipam that is installed as a plugin and runs on all
nodes. It simply forwards requests to the remote lsdsuite-ipam plugin, which
usually runs as a service.

All requests are forwarded, except GetCapabilities and GetDefaultAddressSpaces.
The reason for this is that theses requests are made by Docker on plugin activation,
which might happen before the server is running. The response to these requests is
static and they don't affect the sate of the server, so it's not a problem to handle
them locally.

*/

type Driver struct {
	remote string
	socket string
	nodeID string
	client http.Client
}

func main() {
	remote := os.Getenv("REMOTE")
	socket := os.Getenv("SOCKET")
	nodeID := os.Getenv("NODE_ID")

	_, err := strconv.Atoi(os.Getenv("NODE_ID"))
	if err != nil {
		log.Fatalf("Can't parse NODE_ID: %v", err)
	}

	if remote == "" {
		log.Fatalf("Must specify REMOTE")
	}

	if socket == "" {
		socket = "/run/docker/plugins/ipam.sock"
	}

	NewDriver(remote, socket, nodeID).Run()
}

func NewDriver(remote, socket, nodeID string) *Driver {
	// TODO: check if remote is a valid address
	return &Driver{
		remote: remote,
		socket: socket,
		nodeID: nodeID,
		client: http.Client{
			Timeout: 5 * time.Second,
		},
	}
}

func (d *Driver) Run() {
	log.Println("IPAM-Plugin started, proxying to", d.remote)
	h := ipam.NewHandler(d)
	h.ServeUnix(d.socket, 0) // TODO: 2nd argument is group ID, is 0 OK?
}

// Sends a POST request to `path` (on the remote server), with `data` as
// payload. The payload is JSON-encoded prior to sending. Returns the response's
// body.
func (d *Driver) Request(path string, data interface{}) ([]byte, error) {
	b, err := json.Marshal(data)
	if err != nil {
		return nil, err
	}

	reader := bytes.NewReader(b)
	resp, err := d.client.Post("http://"+d.remote+path, "application/json", reader)

	if err != nil {
		return nil, errors.New(fmt.Sprintf("HTTP request error: %s", err))
	}

	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)

	if err != nil {
		return nil, errors.New(fmt.Sprintf("Read error: %s", err))
	}

	return body, nil
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

	if r.Options == nil {
		// TODO: Is this necessary or is Options always initialized?
		r.Options = make(map[string]string)
	}
	r.Options["lsdsuite-node-id"] = d.nodeID

	body, err := d.Request("/IpamDriver.RequestPool", r)

	if err != nil {
		return nil, err
	}

	resp := ipam.RequestPoolResponse{}
	err = json.Unmarshal(body, &resp)

	if err != nil {
		return nil, errors.New(fmt.Sprintf("JSON error: %s %s", err, string(body)))
	}

	return &resp, nil
}

func (d *Driver) ReleasePool(r *ipam.ReleasePoolRequest) error {
	log.Printf("IPAM: ReleasePool: %+v", r)
	_, err := d.Request("/IpamDriver.ReleasePool", r)
	return err
}

func (d *Driver) RequestAddress(r *ipam.RequestAddressRequest) (*ipam.RequestAddressResponse, error) {
	log.Printf("IPAM: RequestAddress: %+v\n", r)

	body, err := d.Request("/IpamDriver.RequestAddress", r)

	if err != nil {
		return nil, err
	}

	resp := ipam.RequestAddressResponse{}
	err = json.Unmarshal(body, &resp)

	if err != nil {
		return nil, errors.New(fmt.Sprintf("JSON error: %s", err))
	}

	return &resp, nil
}

func (d *Driver) ReleaseAddress(r *ipam.ReleaseAddressRequest) error {
	log.Printf("IPAM: ReleaseAddress: %+v\n", r)

	_, err := d.Request("/IpamDriver.ReleaseAddress", r)
	return err
}
