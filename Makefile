.PHONY: help install dev test docker-dev docker-down clean

help:
	@echo "MediSpecs Backend - Available Commands"
	@echo "======================================"
	@echo "make install      - Install dependencies"
	@echo "make dev          - Run development server"
	@echo "make test         - Run API tests"
	@echo "make docker-dev   - Run with Docker"
	@echo "make docker-down  - Stop Docker containers"
	@echo "make clean        - Clean up generated files"

install:
	pip install -r requirements.txt

dev:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

test:
	python test_api.py

docker-dev:
	docker-compose up --build

docker-down:
	docker-compose down

clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -f *.db *.db-journal
	rm -rf .pytest_cache
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

