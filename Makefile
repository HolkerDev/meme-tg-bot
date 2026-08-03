.PHONY: run lint format typecheck test check cookies install-cookies-cron migrate admin

run:
	uv run meme-nova

lint:
	uv run ruff check src tests

migrate:
	uv run alembic upgrade head

admin:
	cd admin && bin/rails server -b 0.0.0.0 -p 3000

format:
	uv run ruff format src tests

typecheck:
	uv run mypy

test:
	uv run pytest

cookies:
	uv run python scripts/export_instagram_cookies.py

install-cookies-cron:
	@mkdir -p $(CURDIR)/logs
	(crontab -l 2>/dev/null; echo "0 3 * * 0 cd $(CURDIR) && .venv/bin/python scripts/export_instagram_cookies.py >> $(CURDIR)/logs/instagram-cookies.log 2>&1") | crontab -
	@echo "Cron installed. Current crontab:"
	@crontab -l

check: lint typecheck test
