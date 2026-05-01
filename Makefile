.PHONY: run lint format typecheck test check

run:
	uv run meme-nova

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

typecheck:
	uv run mypy

test:
	uv run pytest

check: lint typecheck test
