version_file_name="src/version.js"
regex_number="[0-9]\{1,\}"
expression="${regex_number}\.${regex_number}\.${regex_number}"

# uncomment for debug
# DEBUG=true


version_number=$(cat $version_file_name | grep version | grep -o ${expression})
echo $version_number
