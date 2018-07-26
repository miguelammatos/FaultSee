package support

// Supports makes sure the type of orchestrator being used is supported by the framework we are using
func Supports(orchestrator string) bool {
	currentlySupported := []string{"docker-swarm"}

	// compare all supported  engines
	for _, value := range currentlySupported {
		if orchestrator == value {
			return true
		}
	}
	return false
}
