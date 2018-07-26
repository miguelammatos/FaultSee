# Guide to see experiement results in dashboard

## Launch Dashboard

A server boots listening on port 8081

```
make run
```

The data is loaded from `src/variables` and this folder is mounted as a volume
 in the Docker container that runs the server

## Process experiement results

Replace the experiment number and experiment folder in the following script

```
cd %PROJECT_ROOT/Dashboard

dashboard_pwd=$(pwd)

folder=%PROJECT_ROOT/angainor-lsds/results/$(experiment-date)--hello-faultsee/run-1/

cd %PROJECT_ROOT/angainor-lsds

bash ./bin/lsds process_logs --directory $folder --filename $folder/out.log && cp -v $folder/*.json $dashboard_pwd/src/variables/
```

Check localhost:8081 in your browser


[Template Readme](TEMPLATE-README.md)
