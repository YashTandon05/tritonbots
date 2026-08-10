.PHONY: proto test lint fmt tools clean

proto:
	./scripts/gen_proto.sh

test: proto
	pytest -q

lint:
	ruff check src tests
	mypy src/tbots/core

fmt:
	ruff format src tests
	ruff check --fix src tests

tools:
	./scripts/fetch_tools.sh

clean:
	rm -rf src/tbots/_pb .pytest_cache .ruff_cache
