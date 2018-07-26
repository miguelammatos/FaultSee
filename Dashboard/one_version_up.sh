version_file_name="src/version.js"
regex_number="[0-9]\{1,\}"
expression="${regex_number}\.${regex_number}\.${regex_number}"

# uncomment for debug
# DEBUG=true


function echo_if_debug {
  if [ ! -z "$DEBUG" ]
  then
     echo "$*"
  fi
}



beggining_number_expression="^${regex_number}\.${regex_number}"
last_number_expression="${regex_number}\$"


version_number=$(cat $version_file_name | grep version | grep -o ${expression})
echo_if_debug $version_number

version_beg=$(echo $version_number | grep -o ${beggining_number_expression})
version_last=$(echo $version_number | grep -o ${last_number_expression})

echo_if_debug ${version_beg}
echo_if_debug ${version_last}

new_version_last=$((${version_last} + 1))
echo_if_debug $new_version_last


new_version="${version_beg}.${new_version_last}"

echo "Previous version: $version_number"
echo "New Version: $new_version"


sed_expression="s/${version_number}/${new_version}/g"

sed -i $sed_expression $version_file_name
