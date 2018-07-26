package main

import (
	"ipam/server/driver"
)

func main() {
	// TODO: move port to env var/argument
	driver.New(":7001").Run()
}
