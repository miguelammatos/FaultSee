for folder in */ 
do
	(cd $folder ; docker-compose down)
done
for folder in */ 
do
	(cd $folder ; docker-compose up -d)
done

