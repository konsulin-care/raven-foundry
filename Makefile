.PHONY: help lint format type check test contracts coverage clean install dev

help:
	@echo "Raven Foundry Safeguard Commands"
	@echo "=============================="
	@echo "make install       - Install package in dev mode"
	@echo "make lint        - Run ruff linter"
	@echo "make format     - Run black formatter"
	@echo "make type       - Run mypy type checker"
	@echo "make test       - Run unit tests"
	@echo "make contracts - Run contract tests (enforce AGENTS.md rules)"
	@echo "make coverage  - Run tests with coverage report"
	@echo "make safeguard - Run all quality checks"
	@echo "make clean     - Clean build artifacts"

install:
	pip install -e ".[dev]"

dev: install

lint:
	ruff check src/ tests/

format:
	black src/ tests/

type:
	mypy src/

test:
	pytest tests/ -v --ignore=tests/contracts/

contracts:
	pytest tests/contracts/ -v

coverage:
	pytest tests/ --cov=src/ --cov-report=term-missing --cov-report=html

safeguard: lint format type test contracts
	@echo ""
	@echo "All safeguard checks passed!"

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .mypy_cache
	rm -rf htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
