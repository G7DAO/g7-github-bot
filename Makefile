rebuild:
	docker-compose down
	docker-compose up --build
start:
	docker-compose up --build
teardown:
	docker-compose stop
	docker system prune -a -f