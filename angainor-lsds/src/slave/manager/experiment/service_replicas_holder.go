package experiment

import (
	"fmt"
	"math/rand"
	"slave/manager/debug"
	"sort"

)

// serviceReplicasHolder holds the information of a single service
// 		to save containers status
//		it assumes the index of containers start at 0 and increase at a step of 1
type serviceReplicasHolder struct {
	holderAlive []int
	holderDead  []int
}

func createServiceReplicasHolder(numberStartReplicas int) serviceReplicasHolder {
	initialAliveSlice := make([]int, 0)
	initialDeadSlice := make([]int, 0)

	serviceReplicas := serviceReplicasHolder{
		holderAlive: initialAliveSlice,
		holderDead:  initialDeadSlice,
	}
	serviceReplicas.bornContainers(numberStartReplicas)

	return serviceReplicas
}

func (value *serviceReplicasHolder) numberAlive() int {
	return len(value.holderAlive)
}

// returns a random @amount alive containers (the service slots numbers)
func (value serviceReplicasHolder) randomContainers(amount int) []int {
	// we want the list to be sorted every time we pick a random number

	sort.Ints(value.holderAlive)
	debug.ServiceReplicasHolderDebug("Producing ", amount, " random containers")
	// create a list in random order, to randomly choose index
	randomIndexList := rand.Perm(len(value.holderAlive))
	debug.ServiceReplicasHolderDebug("Perm ", randomIndexList)
	containersList := make([]int, amount)

	// we only need @amount, so just pick the first N (N=@amount)
	for index := 0 ; index < amount ; index++ {
		indexInAlive := randomIndexList[index]
		containersList[index] = value.holderAlive[indexInAlive]
	}
	debug.ServiceReplicasHolderDebug("Alive   : ", value.holderAlive)
	debug.ServiceReplicasHolderDebug("Produced: ", containersList)

	return containersList
}

func (value *serviceReplicasHolder) validateAlive(slot int) error {
	for _, a := range value.holderAlive {
		if a == slot {
			// it is alive, no need to raise an error
			return nil
		}
	}
	err := fmt.Errorf("Slot %d is not alive", slot)
	return err
}

func findMaxContainerNumberDeadOrAlive(array1 []int, array2 []int) int {
	m1 := findMaxContainerNumber(array1)
	m2 := findMaxContainerNumber(array2)
	if m1 > m2 {
		return m1
	} else {
		return m2
	}
}

func findMaxContainerNumber(array []int) (max int) {
	max = -1
	for _, element := range array {
		if element > max {
			max = element
		}
	}
	return max
}

// does not validate anything!
func (value *serviceReplicasHolder) bornContainers(amount int) {
	// index_1 now holds the amount of added (slots that were dead)

	// find max before
	newSlot := findMaxContainerNumberDeadOrAlive(value.holderDead, value.holderAlive) + 1
	needToAdd := amount
	debug.ServiceReplicasHolderDebug("First New Slot", newSlot)
	for index := 0; index < needToAdd; index++ {
		debug.ServiceReplicasHolderDebug("Added", newSlot)
		value.holderAlive = append(value.holderAlive, newSlot)
		newSlot++
	}
	debug.ServiceReplicasHolderDebug("After all born", *value)
}

//// does not validate anything!
//func (value *serviceReplicasHolder) bornContainers(amount int) {
//	// First Fill the empty slots (provided by dead)
//
//	// we want to reborn the first containers first
//	sort.Ints(value.holderDead)
//
//	index_1 := 0
//	for ; index_1 < amount && index_1 < len(value.holderDead); index_1++ {
//		debug.ServiceReplicasHolderDebug("Holder Container reborn: ", value.holderDead[index_1])
//		value.holderAlive = append(value.holderAlive, value.holderDead[index_1])
//	}
//
//	// index_1 now holds the amount of added (slots that were dead)
//
//	// remove the first N from the dead list
//	value.holderDead = removeFirstN(value.holderDead, index_1)
//
//	// we might need to add some extra
//	stillNeedToAdd := amount - index_1
//	debug.ServiceReplicasHolderDebug("Still neet to add", stillNeedToAdd)
//	firstEmptyAliveSlot := len(value.holderAlive)
//	newSlot := firstEmptyAliveSlot
//	debug.ServiceReplicasHolderDebug("First Empty", newSlot)
//	for index_2 := 0; index_2 < stillNeedToAdd; index_2++ {
//
//		debug.ServiceReplicasHolderDebug("Added", newSlot)
//		value.holderAlive = append(value.holderAlive, newSlot)
//
//		newSlot++
//	}
//	debug.ServiceReplicasHolderDebug("After all born", value)
//}

// does not validate anything!
func (value *serviceReplicasHolder) killContainers(slots []int) {

	debug.ServiceReplicasHolderDebug("Before kill scenario ", *value)
	debug.ServiceReplicasHolderDebug("kill: ", slots)

	for _, slotToKill := range slots{
		index := findIndex(value.holderAlive, slotToKill)
		value.holderAlive = removeElementAtIndex(value.holderAlive, index)
		value.holderDead = append(value.holderDead, slotToKill)
		debug.ServiceReplicasHolderDebug("Holder Container Killed: ", slotToKill)
	}
	debug.ServiceReplicasHolderDebug("After kill scenario ", *value)

}

func findIndex(s []int, element int) int {
	for index, value := range s {
		if value == element {
			return index
		}
	}
	return -1
}

func removeElementAtIndex(s []int, index int) []int{
	//swap the index with the last
	s[index] = s[len(s)-1]
	// We do not need to put s[i] at the end, as it will be discarded anyway
	return s[:len(s)-1]
}

func removeFirstN(s []int, numberToRemove int) []int {
	return s[numberToRemove:]
}
