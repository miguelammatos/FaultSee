package main

import (
	"fmt"
	"github.com/docker/engine/client"
	"slave/manager"
)
//import (
//	"fmt"
//	"github.com/docker/engine/client"
//	"slave/manager"
//)

func main() {
	fmt.Println("FaultseeSlaveVersion", FaultseeSlaveVersion)
	cli, err := client.NewEnvClient()
	if err != nil {
		panic(err)
	}

	manager := manager.New(cli, FaultseeSlaveVersion)
	manager.Run()
}


//func main() {
//	fmt.Println("FaultseeSlaveVersion", FaultseeSlaveVersion)
//
//	experiment.EntryThemain()
//}
