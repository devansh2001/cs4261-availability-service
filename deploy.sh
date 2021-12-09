#heroku login;
heroku container:login;
docker build -t availability-service .;
docker tag availability-service registry.heroku.com/cs4261-availability-service/web;
docker push registry.heroku.com/cs4261-availability-service/web;
heroku container:release web -a cs4261-availability-service;
#heroku logs --tail --app cs4261-availability-service;