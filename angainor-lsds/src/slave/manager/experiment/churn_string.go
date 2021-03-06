package experiment

const example_churn_string = `
environment:
    seed: 568
    ntp_server: europe.pool.ntp.org
events:
    - beginning:
        load-balancer: 1
        web-server: 2
        database: 3
    - moment:
        time: 100
        services:
            load-balancer:
                - start:
                      amount: 19
            database:
                - start:
                    percentage: 30
    - moment:
        time: 100
        services:
            load-balancer:
                - start:
                      amount: 1
            web-server:
                - start:
                    amount: 19
            database:
                - start:
                    percentage: 30
    - moment:
        time: 300
        mark: "300 seconds elapsed"

    - moment:
        time: 500
        services:
            web-server:
                - fault:
                    target:
                        specific: [1, 2]
                    kill:
                - fault:
                    target:
                        specific: [4, 5]
                    signal:
                        kills_container: "yes"
                        signal: SIGINT
                - fault:
                    target:
                        specific: [3]
                    cpu:
                        duration: 30
                - fault:
                    target:
                        specific: [6]
                    custom:
                        kills_container: "no"
                        fault_file_name: waste_cpu
    - moment:
        time: 800
        mark: "removing containers"
        services:
            load-balancer:
                - stop:
                    specific: [2]
            web-server:
                - stop:
                    amount: 10
            database:
                - stop:
                    percentage: 30

    - end: 1500

`