
@echo off
echo === SHVEYA localhost:8000 — proverka bez Docker ===
echo Ustanavlivayu zavisimosti...
pip install fastapi uvicorn --quiet
echo.
echo Zapuskayu API na http://localhost:8000/
echo Otkroy browser: http://localhost:8000/ + http://localhost:8000/docs
echo.
python -m uvicorn api_main_check:app --reload --port 8000
pause
