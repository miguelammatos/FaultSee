# Copyright (c) 2007-2013 Alysson Bessani, Eduardo Alchieri, Paulo Sousa, and the authors indicated in the @author tags
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#/bin/bash
echo "Set value $REPLICA_INDEX"
REPLICA_INDEX=$((REPLICA_INDEX-1))
echo "After decrement $REPLICA_INDEX"

if [ -z "$REPLICA_INDEX" ]
then
      echo "Max heap: $MAX_HEAP_SIZE"
      echo "Replica: $REPLICA_INDEX"
      echo "\$REPLICA_INDEX must be set to a number"
      echo "Current configs for each index are present in ./config/hosts.config printed next"
      cat ./config/hosts.config
      exit 1
else
      echo "Starting replica NBR $REPLICA_INDEX"
fi

java -Dlogback.configurationFile="./config/logback.xml" -cp bin/:lib/* bftsmart.demo.ycsb.YCSBServer $REPLICA_INDEX
