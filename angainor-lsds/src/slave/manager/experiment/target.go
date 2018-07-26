package experiment

import (
	"fmt"
	"math"
	"slave/manager/debug"
)

const replicas_spaces = "          "

// Interface that allows
type eventTarget interface {
	// calculates the int of number it affects
	NumberAffected(previousHolder serviceReplicasHolder) int

	// calculateAdd is a function that returns the holder after add is applied
	calculateAdd(previousHolder serviceReplicasHolder) (serviceReplicasHolder, error)
	// calculateIdle is a function that returns replicasAffected without modifying the holder
	calculateIdle(previousHolder serviceReplicasHolder) ([]int, error)
	// calculateKill is a function that returns the holder and replicasAffected after an operation that kills is applied
	calculateKill(previousHolder serviceReplicasHolder) (serviceReplicasHolder, []int, error)

	// method that helps logging
	String() string

}
type amountReplicas struct {
	Amount int
}
type percentageReplicas struct {
	Percentage int
}
type slotSpecifReplicas struct {
	SlotNumbers []int `yaml:"specific"`
}


func (value amountReplicas) String() string {
	return fmt.Sprintf("Amount: %d", value.Amount)
}
func (value percentageReplicas) String() string {
	return fmt.Sprintf("Percentage: %d%%", value.Percentage)
}
func (value slotSpecifReplicas) String() string {
	return fmt.Sprintf("Specific: %v", value.SlotNumbers)
}

func (value *percentageReplicas) calculatePercentageInContainers(previousAmount int) int {
	percentage := float64(value.Percentage)
	oneHundred := float64(100)
	previous := float64(previousAmount)

	return int(math.Ceil((percentage / oneHundred) * previous))
}


// returns a @amount of random containers
func calculateSlots(previousHolder serviceReplicasHolder, amount int) ([]int, error) {

	//// validate there is at least
	//if previousHolder.numberAlive() <= 0  {
	//	err := fmt.Errorf("CalculateSlots: At least one replica must be alive")
	//	return nil, err
	//}
	if amount > previousHolder.numberAlive() {
		err := fmt.Errorf("CalculateSlots: There are not enough containers alive as requested. Alive %d, Requested: %d", previousHolder.numberAlive(), amount)
		return nil, err
	}

	// calculate affected
	affectedSlots := previousHolder.randomContainers(amount)

	return affectedSlots, nil
}

func (value amountReplicas) calculateIdle(previousHolder serviceReplicasHolder) ([]int, error) {
	return calculateSlots(previousHolder, value.Amount)
}

func (value percentageReplicas) calculateIdle(previousHolder serviceReplicasHolder) ([]int, error) {
	amount := value.calculatePercentageInContainers(previousHolder.numberAlive())
	return calculateSlots(previousHolder, amount)
}

func (value slotSpecifReplicas) calculateIdle(previousHolder serviceReplicasHolder) ([]int, error) {
	for _, slot := range value.SlotNumbers {
		err := previousHolder.validateAlive(slot)
		if err != nil {
			return nil, err
		}
	}
	return value.SlotNumbers, nil
}


func (value amountReplicas) calculateAdd(previousHolder serviceReplicasHolder) (serviceReplicasHolder, error) {
	previousHolder.bornContainers(value.Amount)
	return previousHolder, nil
}
func (value percentageReplicas) calculateAdd(previousHolder serviceReplicasHolder) (serviceReplicasHolder, error) {
	numberToAdd := value.calculatePercentageInContainers(len(previousHolder.holderAlive))
	previousHolder.bornContainers(numberToAdd)
	return previousHolder, nil
}
func (value slotSpecifReplicas) calculateAdd(previousHolder serviceReplicasHolder) (serviceReplicasHolder, error) {
	err := fmt.Errorf("Replicas: Error calculateAdd %s is not compatible with add operation", typeof(value))
	return serviceReplicasHolder{}, err
}


func (value amountReplicas) calculateKill(previousHolder serviceReplicasHolder) (serviceReplicasHolder, []int, error) {
	if value.Amount > previousHolder.numberAlive() {
		err := fmt.Errorf("Remove: Trying to remove too many instances. Alive: %d Remove: %d", previousHolder.holderAlive, value.Amount)
		return serviceReplicasHolder{}, nil, err
	}
	listToKill := previousHolder.randomContainers(value.Amount)

	previousHolder.killContainers(listToKill)

	return previousHolder, listToKill, nil
}
func (value percentageReplicas) calculateKill(previousHolder serviceReplicasHolder) (serviceReplicasHolder, []int, error) {
	amount := value.calculatePercentageInContainers(previousHolder.numberAlive())
	if amount > previousHolder.numberAlive() {
		err := fmt.Errorf("Remove: Trying to remove too many instances. Alive: %d Remove: %d", previousHolder.holderAlive, amount )
		return serviceReplicasHolder{}, nil, err
	}
	listToKill := previousHolder.randomContainers(amount)

	previousHolder.killContainers(listToKill)

	return previousHolder, listToKill, nil
}
func (value slotSpecifReplicas) calculateKill(previousHolder serviceReplicasHolder) (serviceReplicasHolder, []int, error) {
	for _, slot := range value.SlotNumbers {
		err := previousHolder.validateAlive(slot)
		if err != nil {
			return serviceReplicasHolder{}, nil, err
		}
	}
	// All are alive, now we kill them
	previousHolder.killContainers(value.SlotNumbers)
	return previousHolder, value.SlotNumbers, nil
}

func (value *amountReplicas) build(raw interface{}) error {
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("ParseReplicas: Error Building %s. Error: %v. Input: %s", typeof(value), err, raw)
		return err2
	}
	if value.Amount < 1 {
		err2 := fmt.Errorf("ParseReplicas: Error Building %s. Error: Amount must be 1 or more. Input: %s", typeof(value), raw)
		return err2
	}
	debug.ParseChurnDebug(replicas_spaces, typeof(value), value)
	return nil
}

func (value *percentageReplicas) build(raw interface{}) error {
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("ParseReplicas: Error Building %s. Error: %v. Input: %s", typeof(value), err, raw)
		return err2
	}
	if value.Percentage < 1 {
		err2 := fmt.Errorf("ParseReplicas: Error Building %s. Error: Percentage must be bigger than 1. Input: %s", typeof(value), raw)
		return err2
	}
	debug.ParseChurnDebug(replicas_spaces, typeof(value), value)
	return nil
}

func (value *slotSpecifReplicas) build(raw interface{}) error {
	err := ParseIntoCorrectStruct(raw, &value)
	if err != nil {
		err2 := fmt.Errorf("ParseReplicas: Error Building %s. Error: %v. Input: %s", typeof(value), err, raw)
		return err2
	}
	for _, value := range value.SlotNumbers {
		if value < 0 {
			err3 := fmt.Errorf("ParseReplicas: Error Building %s. Error: Slot Numbers must be 0 or positive number. Input: %s", typeof(value), raw)
			return err3
		}
	}
	debug.ParseChurnDebug(replicas_spaces, typeof(value), value)
	return nil
}

func (value amountReplicas) NumberAffected(_ serviceReplicasHolder) int {
	return value.Amount
}
func (value percentageReplicas) NumberAffected(previousHolder serviceReplicasHolder) int {
	amount := value.calculatePercentageInContainers(previousHolder.numberAlive())
	return amount
}

func (value slotSpecifReplicas) NumberAffected(_ serviceReplicasHolder) int {
	return len(value.SlotNumbers)
}

func parseReplicas(raw map[string]interface{}) (eventTarget, error) {

	if len(raw) != 1 {
		err := fmt.Errorf("ParseReplicas: Replicas Map must have exactly 1 element, has %d elements. Input: %s", len(raw), raw)
		return nil, err
	}
	for replicasType := range raw {
		switch replicasType {
		case "amount":
			var amount amountReplicas
			if err := amount.build(raw); err != nil {
				return nil, err
			}
			return amount, nil
		case "percentage":
			var percentage percentageReplicas
			if err := percentage.build(raw); err != nil {
				return nil, err
			}
			return percentage, nil
		case "specific":
			var slotsSpecific slotSpecifReplicas
			if err := slotsSpecific.build(raw); err != nil {
				return nil, err
			}
			return slotsSpecific, nil
		default:
			err := fmt.Errorf("ParseReplicas: '%s' not support as replica type. Input: %s", replicasType, raw)
			return nil, err
		}
	}
	err := fmt.Errorf("ParseReplicas: CRITICAL ERROR, Return only present to satisfy compiler. If this error message is ever presented to you please revise the code. Input: %s", raw)
	return nil, err
}
