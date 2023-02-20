migrations:
	python3 manage.py makemigrations
migrate: 
	python3 manage.py migrate
admin:
	python3 manage.py createadmin
loaddata:
	python3 manage.py loaddata loads.json
run:
	make migrations && \
	make migrate && \
	make loaddata && \
	make admin && \
	python3 manage.py runserver 0.0.0.0:8000
static: 
	python3 manage.py collectstatic
test:
	docker compose -f docker-compose-test.yaml up \
	--abort-on-container-exit \
    --exit-code-from api_test && \
	docker compose -f docker-compose-test.yaml down -v || \
	docker compose -f docker-compose-test.yaml down -v