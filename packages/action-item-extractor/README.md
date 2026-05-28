# Action Item Extractor

A CLI tool that extracts structured action items from messy standup notes using Google Gemini Flash and Pydantic.

This package is part of the `utils-workspace`.

## Setup

1.  **Sync the workspace**:
    From the **root** of the `utils` workspace, run:
    ```bash
    uv sync
    ```

2.  **Set up your Google Gemini API Key**:
    - Obtain a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
    - Create a `.env` file in this directory (`packages/action-item-extractor/`) or export it as an environment variable:
      ```bash
      echo "GOOGLE_API_KEY='your-api-key-here'" > .env
      ```

## Usage

Run the tool from the **root** of the workspace using `uv run`. Use the `--directory` (or `-C`) flag to ensure the local `.env` is loaded.

```bash
uv run --directory packages/action-item-extractor action-item-extractor
```

## Features
- **Structured Data**: Uses Pydantic for strict schema validation.
- **Resilient Parsing**: Uses Gemini 1.5 Flash for high-speed, accurate extraction.
- **Messy Note Support**: Handles incomplete sentences, mixed ownership, and vague deadlines.
