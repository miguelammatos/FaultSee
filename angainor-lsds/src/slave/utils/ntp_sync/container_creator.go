package ntp_sync

import (
	"context"
	"fmt"
	"github.com/pkg/errors"
	"io/ioutil"
	"log"
	"time"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/api/types/container"
	"github.com/docker/engine/client"
)

func downloadImage(cli *client.Client, containerImageName string) error{
	rc, err := cli.ImagePull(context.Background(), containerImageName , types.ImagePullOptions{})
	if err != nil {
		fmt.Println("Error: ", err.Error())
		return err
		//cmd.Response <- resp("err", err.Error())
	}

	// The output isn't important for lsdsuite-master, but we consume it to
	// make sure the operation has finished
	body, err := ioutil.ReadAll(rc)
	if err != nil {
		fmt.Println("Error: ", err.Error())
		return err
		//cmd.Response <- resp("err", err.Error())
	}

	fmt.Println("Image pull result:", string(body))
	return nil
}

func checkImageExistsLocally(cli *client.Client, containerImageName string) error {
	ctx := context.Background()
	_, _, err := cli.ImageInspectWithRaw(ctx, containerImageName)
	return err
}

// This will launch the container that will sinchronize the ntp clock
func LaunchContainer(cli *client.Client, containerImageName string) error{

	errorImageExists := checkImageExistsLocally(cli, containerImageName)
	if errorImageExists != nil {
		fmt.Println("Image does not exist")
		// image does not exist
		errorDownload := downloadImage(cli, containerImageName)
		if errorDownload != nil {
			// failed to download
			return errorDownload
		}
	}

	ctx := context.Background()
	resp, err := cli.ContainerCreate(ctx, &container.Config{
		Image:        containerImageName,
	}, &container.HostConfig{
		CapAdd: []string{"SYS_TIME", "SYS_NICE"},
	}, nil, "faultsee-ntp-sync")
	if err != nil {
		return err
	}

	if err := cli.ContainerStart(ctx, resp.ID, types.ContainerStartOptions{}); err != nil {
		return err
	}


	ctx, cancel := context.WithTimeout(context.Background(), 5000*time.Millisecond)
	defer cancel()

	// this function will block until either container stops or Timeout from ctx
	statusCode, errWait := cli.ContainerWait(ctx, resp.ID)

	var errorMessage string
	errorMessage = ""

	if errWait != nil {
		errorMessage = errorMessage + "Error Waiting for NTP Sync Container to stop : " + errWait.Error() + " "
	}


	errCTX := ctx.Err()
	if errCTX != nil {
		log.Println("Error ContextTimeout: ", errCTX.Error())
		errorMessage = errorMessage + "Error Timeout Context: " + errCTX.Error() + " "
	} else {
		log.Println("NTP Sync Container Terminated STATUS CODE: ", statusCode )
	}


	log.Println("Removing ", resp.ID)
	err = cli.ContainerRemove(context.Background(), resp.ID, types.ContainerRemoveOptions{
		Force: true,
	} )

	if err != nil {
		log.Println("Error Removing NTP Sync Container: ", err.Error())
		errorMessage = errorMessage + "Error Removing NTP Sync Container: " + err.Error() + " "
	}

	if errorMessage != "" {
		return errors.New(errorMessage)
	}
	return nil
}
