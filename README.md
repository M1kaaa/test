# Patch Cord Calculator

Web application for calculating patch-cord length between servers in a data center.

## Features

- Supports same-rack and cross-rack scenarios
- Cable route visualization
- Recommended standard patch-cord length
- Rack list loaded from `racks-condition (10).xlsx` (`02b03` to `02b18`)

## Requirements

- Windows 10/11
- Python 3.11+
- Web browser

## Installation (from source)

```bash
pip install -r requirements.txt
```

## Run

### Option 1 (recommended on Windows)

Double-click the Windows launcher batch file in the project root:
- `zapusit.bat` (or the default launcher `.bat` file shipped with the project)

### Option 2 (Python)

```bash
python run_app.py
```

The browser opens automatically after startup.

## Portable build (no Python required)

Use file from `dist`:

- `PatchCordCalculatorPortable.zip`

How to use:

1. Unzip the archive
2. Run `PatchCordCalculator.exe`
3. Wait for the browser to open

## Project structure

- `cable_calculator.py` - calculation logic
- `rack_plan.py` - rack loading/filtering from Excel
- `web_api.py` - FastAPI backend
- `web_interface_v2.html` - main frontend
- `run_app.py` - unified launcher
- Windows launcher `.bat` file - quick start on Windows

## Notes

- API and web server run on localhost
- If firewall warning appears, allow local access

## License

Internal use.
