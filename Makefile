.PHONY: all format lint types imports test

all: format lint types imports test

format:
	uv run ruff format .

lint:
	uv run ruff check . --fix

types:
	uv run ty check

imports:
	uv run lint-imports

test:
	uv run pytest
