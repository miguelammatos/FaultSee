package faults

import (
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
)


//calculateMD5 reads all the files in the file tree rooted at root and returns an MD5 hash of the CONTENTS of the files (sorted alphabetically)
func CalculateMD5(faultsFolder string) (string, error){
	var files []string

	root := faultsFolder
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		files = append(files, path)
		return nil
	})
	if err != nil {
		return "", err
	}

	sort.Strings(files)


	hash := md5.New()
	for _, fileName := range files {
		fmt.Println(fileName)
		fileD, err := os.Open(fileName)

		if err != nil {
			return "", err
		}



		_, err = io.Copy(hash, fileD)
		errF := fileD.Close()
		if errF != nil {
			return "", errF
		}
	}

	stringResult := hex.EncodeToString(hash.Sum(nil))

	return stringResult, nil
}