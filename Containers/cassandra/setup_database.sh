sleep 10
echo "CASANDRA_HOSTNAME: $CASANDRA_HOSTNAME"
cqlsh --file=setup_database.cql $CASANDRA_HOSTNAME
echo "Show again"
cqlsh --file=setup_database.cql $CASANDRA_HOSTNAME
echo "Its done"
exit 0
