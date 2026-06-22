# Parsers API

A FastAPI-based web service for parsing data from various Russian government and public services, including customs (FTS), traffic police (GIBDD), bailiffs (FSSP), and more. This API supports both synchronous and asynchronous parsing with built-in proxy rotation, caching, and machine learning-powered captcha solving.

## Features

- **Multiple Parsers**: Support for EPTS, FSSP, FTS, GIBDD, and NSIS parsers.
- **Synchronous & Asynchronous Parsing**: Handle requests in real-time or queue them for background processing.
- **Proxy Rotation**: Automatic proxy cycling to avoid rate limits and blocks.
- **Captcha Solving**: Integrated machine learning models for solving captchas (e.g., for GIBDD).
- **Caching**: Built-in result caching to reduce redundant requests.
- **Threading**: Background workers for token updates and task processing.
- **RESTful API**: Clean, documented endpoints using FastAPI.

## Installation

### Prerequisites

- Python 3.11+
- Virtual environment (recommended)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/parsers-api.git
   cd parsers-api
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv env
   env\Scripts\activate  # On Windows
   # source env/bin/activate  # On macOS/Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r req.txt
   ```

4. (Optional) For specific parsers, install additional requirements if needed (e.g., in parserFTS/req.txt).

5. Ensure models are in place: Place your ML models (e.g., `model_GIBDD.keras`) in the `models/` directory.

6. Configure proxies: Update `proxy.py` with your proxy list.

## Usage

### Running the Server

Start the FastAPI server:
```bash
uvicorn app:app --host 0.0.0.0 --port 10221 --workers 1
```

The API will be available at `http://localhost:10221`.

### API Endpoints

#### Synchronous Parsing
- **GET /parse/**: Parse data synchronously.
  - Parameters: `parser_type`, `vin`, `name`, `last_name`, `middle_name`, `birthdate`, `cache`
  - Example: `/parse/?parser_type=GIBDD&vin=XXXXXXXXXXXXXXXXX`

#### Asynchronous Parsing
- **GET /create_task/**: Create an asynchronous parsing task.
  - Parameters: Same as above.
  - Returns: `task_id`

- **GET /task_status/{task_id}**: Get the status and result of a task.
  - Returns: Task status, result, or error.

#### FTS Specific
- **GET /parseFTS/**: Synchronous parsing for FTS.
  - Parameters: Similar to /parse/

### Example Request

```python
import requests

# Synchronous example
response = requests.get("http://localhost:10221/parse/", params={
    "parser_type": "GIBDD",
    "vin": "YOUR_VIN_HERE"
})
print(response.json())
```

### Supported Parsers

- **EPTS**: Electronic Passport of Vehicle.
- **FSSP**: Federal Bailiff Service.
- **FTS**: Federal Customs Service.
- **GIBDD**: State Traffic Inspectorate (with captcha solving).
- **NSIS**: National Social Insurance Service.

## Configuration

- **Proxies**: Edit `proxy.py` to add your proxy list.
- **Models**: Ensure ML models are loaded correctly in `factory/modelFactory.py`.
- **Database**: Uses SQLite (`tasks.db`) for task management and caching.

## Development

### Project Structure

```
parsers-api/
├── app.py                 # Main FastAPI app
├── baseParser.py          # Base parser class
├── proxy.py               # Proxy configuration
├── req.txt                # Main requirements
├── schema.py              # Pydantic models
├── workers.py             # Background workers
├── factory/
│   ├── modelFactory.py    # Model factory
│   └── parserFactory.py   # Parser factory
├── models/                # ML models
├── parser*/               # Individual parser modules
├── utils/                 # Utilities (response builder, task helper)
```

### Adding a New Parser

1. Create a new parser class inheriting from `BaseParser`.
2. Implement the `parse` method.
3. Register it in `parserFactory.py`.
4. Add any required models in `modelFactory.py`.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push to the branch.
5. Open a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational and research purposes only. Ensure compliance with the terms of service of the target websites and applicable laws.
