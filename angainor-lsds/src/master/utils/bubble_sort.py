
# comparission_value_function is a function that returns the value to be used in comparisions
def bubbleSort(arr, comparission_value_function):
    n = len(arr)

    # Traverse through all array elements
    for i in range(n):

        # Last i elements are already in place
        for j in range(0, n - i - 1):

            # traverse the array from 0 to n-i-1
            # Swap if the element found is greater
            # than the next element
            if comparission_value_function(arr[j]) > comparission_value_function(arr[j + 1]):
                arr[j], arr[j + 1] = arr[j + 1], arr[j]