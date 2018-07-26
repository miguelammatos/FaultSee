package bubble_sort


type Sortable interface{
	Len() int

	Swap(i, j int)
	Less(i, j int) bool
}

func BubbleSort(tosort Sortable) {
	size := tosort.Len()
	if size < 2 {
		return
	}

	for i := 0; i < size; i++ {
		for j := size - 1; j >= i+1; j-- {
			if tosort.Less(j, j-1) {
				tosort.Swap(j, j-1)
			}
		}
	}
}



//// Required functions to apply sort.Sort()
//func (s RawMoments) Len() int             { return len(s) }
//func (s RawMoments) Swap(i, j int)        { s[i], s[j] = s[j], s[i] }
//func (s RawMoments) Iterate() []RawMoment { return s }
//func (s RawMoments) Less(i, j int) bool   {
//	return s[i].time() < s[j].time()
//}

