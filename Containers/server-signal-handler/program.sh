#!/usr/bin/env sh
# set -x

pid=0

# SIGUSR1 -handler
my_handler() {
  echo "my_custom_handler"
}

# SIGTERM -handler
term_handler() {
  if [ $pid -ne 0 ]; then
    kill -SIGTERM "$pid"
    wait "$pid"
  fi
  exit 0; # 128 + 15 -- SIGTERM
}

# setup handlers
# on callback, kill the last background process, which is `tail -f /dev/null` and execute the specified handler
trap 'kill ${!}; my_handler' SIGUSR1
trap 'kill ${!}; term_handler' SIGTERM

# run application
node program &
pid="$!"

# wait forever
while true
do
    tail -f /dev/null & wait ${!}
done
