# Tixte Exporter

A tool to download all your files from Tixte using the data package export.

## Overview

This script helps you download all your uploaded files from Tixte using the CSV file provided in your Tixte data package. It features:

- Progress tracking with download speed display
- Skipping already downloaded files
- Configurable delay between downloads to avoid rate limiting
- Checking for files in local directories to avoid duplicate downloads
- Comprehensive integrated logging system with detailed logs and summary statistics

## Requirements

- Python 3.6+
- Required packages:
  - requests
  - rich

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/TheInternetUse7/tixte-export.git
   cd tixte-export
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Request your data package from Tixte (Account Settings > Privacy > Request Data Package)
2. Extract the data package to a directory
3. Create a `config.json` file (see Configuration section)
4. Run the script:
   ```
   python tixte_exporter.py --csv path/to/uploads.csv
   ```

### Command Line Arguments

```
python tixte_exporter.py [OPTIONS]
```

Options:
- `--csv`: Path to uploads CSV file (default: "data/uploads.csv")
- `--output`: Directory to save downloaded files (default: "exported_files")
- `--delay`: Base delay between downloads in seconds (default: 1.0)
- `--jitter`: Maximum random jitter added to delay in seconds (default: 0.5)
- `--max-retries`: Maximum retries per file (default: 5)
- `--user-agent`: Custom User-Agent string (default: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
- `--dry-run`: List files without downloading


## Configuration

Create a `config.json` file in the same directory as the script with the following structure:

```json
{
  "subdomain": "your-tixte-subdomain",
  "local_check_dir": "path/to/local/files"
}
```

- `subdomain`: Your Tixte subdomain (required if not specified in the CSV)
- `local_check_dir`: Optional directory to check for existing files before downloading

## Features

- **Download Speed Display**: Shows real-time download speed for each file
- **Smart Skipping**: Avoids downloading files that:
  - Have already been downloaded (tracked in `downloaded.log`)
  - Exist in the output directory
  - Exist in the specified local directory
- **Exponential Backoff**: Automatically retries failed downloads with increasing delays
- **Progress Visualization**: Uses Rich library for beautiful progress display
- **Comprehensive Logging System**: Automatically logs all download attempts, results, and errors in `detailed.log` without requiring additional flags

## Example

```
python tixte_exporter.py --csv data/uploads.csv --output my_tixte_files --delay 2.0
```

The script will automatically create a detailed log file (`detailed.log`) that contains comprehensive information about the download process, including connection details, download speeds, and any errors encountered.

## License

MIT License
