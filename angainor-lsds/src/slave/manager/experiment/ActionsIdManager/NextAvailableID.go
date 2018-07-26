package ActionsIdManager

type singleton struct {
	nextID int
}

var instance *singleton

// <--- NOT THREAD SAFE
func getInstance() *singleton {
	if instance == nil {
		instance = &singleton{
			nextID: 0,
		}
	}
	return instance
}

func Reset() {
	getInstance().nextID = 0
}

func NextAvailableID() int {
	controller := getInstance()
	toReturn := controller.nextID
	controller.nextID = toReturn + 1
	return toReturn
}
