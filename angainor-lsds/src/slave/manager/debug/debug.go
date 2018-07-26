package debug

import (
	"fmt"
)

const parseChurnDebug = false
const containersAliveDead = false
const serviceReplicasHolder = false
// print the state of all services between Actions
const stateAllServices = false

// ParseChurnDebug controls
func ParseChurnDebug(msg ...interface{}) {
	if parseChurnDebug {
		fmt.Println(msg)
	}
}

// ContainersAliveDeadDebug controls
func ContainersAliveDeadDebug(msg ...interface{}) {
	if containersAliveDead {
		fmt.Println(msg)
	}
}

func ServiceReplicasHolderDebug(msg ...interface{}) {
	if serviceReplicasHolder {
		fmt.Println(msg)
	}
}

func StateService(msg ...interface{}) {
	if stateAllServices {
		fmt.Println(msg)
	}
}
