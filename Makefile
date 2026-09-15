serve:
	uv run uvicorn main:app --reload
kill:
	kill -9 $(lsof -t -i:8000)