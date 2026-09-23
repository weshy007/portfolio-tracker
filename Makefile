serve:
	uv run uvicorn main:app --reload
kill:
	sudo lsof -t -i tcp:8000 | xargs kill -9