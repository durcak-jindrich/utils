# Action Item Extractor

A CLI tool that extracts structured action items from messy standup notes using Google Gemini Flash and Pydantic.

## Setup

1.  Navigate to this directory:
    ```bash
    cd packages/action-item-extractor
    ```

2.  Install dependencies (using `uv` or `pip`):
    ```bash
    uv pip install -e .
    ```
    *Note: Ensure you have `uv` installed, or use a standard virtual environment with `pip`.*

3.  Set up your Google Gemini API Key:
    - Obtain a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
    - Create a `.env` file in this directory or export it as an environment variable:
      ```bash
      echo "GOOGLE_API_KEY='your-api-key-here'" > .env
      ```

## Usage

Run the script directly to see the demo with sample notes:

```bash
python src/action_item_extractor/main.py
```

## Features
- **Structured Data**: Uses Pydantic for strict schema validation.
- **Resilient Parsing**: Uses Gemini 1.5 Flash for high-speed, accurate extraction.
- **Messy Note Support**: Handles incomplete sentences, mixed ownership, and vague deadlines.
