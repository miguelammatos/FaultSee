# docker-ntpd
alpine based ntpd docker container

Run the container
------------------

The container needs privileged rights to be able to update the hosts time. So an example run statement is:

```shell
docker run --cap-add SYS_TIME -d mapa12/ntp-sync
```

This statement creates a container named ntpd from the cguenther/ntpd image privileged and detached (-d) mode and resarts it always.

Custom Configuration
--------------

The default configuration uses the /etc/ntpd.conf file with a predefined public ntp server: ```servers pool.ntp.org```. For custom configuration purposes the /etc/ntpd.conf file needs to be replaced by a specific volume mapping. For example the ```-v <<PATH_TO_MY_NTPD_CONF>>/ntpd.conf:/etc/ntpd.conf``` flag can be used in the run statement.

Currently the daemon is started in daemon mode (-d), using the /etc/ntpd.conf (-f) file for ntpd configuration and updating as soon as the container starts (-s). Those ntpd flags can be overridden with custom commands. Those can be appended at the run statement.
