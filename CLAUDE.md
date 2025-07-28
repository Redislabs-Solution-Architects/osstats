# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OSStats is a Python tool for extracting Redis database metrics. It connects to Redis databases (both single instance and clustered), collects command statistics over a specified time period, and generates Excel reports with throughput analysis.

## Core Commands

### Running the Application
```bash
# Basic usage with default 5-minute duration
python osstats.py

# Custom duration (in minutes)
python osstats.py -d 10

# Print results to console only (no Excel file)
python osstats.py -po

# Custom configuration file
python osstats.py -c my_config.ini

# Custom output file name
python osstats.py -o MyResults.xlsx
```

### Docker Usage
```bash
# Build and run with Docker
docker run -v /path/to/osstats:/app -t sumitshatwara/redis-osstats python3 osstats.py
```

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .env && source .env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit configuration
cp config.ini.example config.ini

# Deactivate when done
deactivate
```

### Testing
```bash
# Run all tests with pytest
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest test_osstats.py

# Run load generator (generates Redis test data, ~1 minute)
./load-generator.sh
```

### Code Formatting
```bash
# Check code formatting
black --check .

# Format code
black .

# Check specific file
black --check osstats.py
```

## Architecture

### Core Components

**Main Script (`osstats.py`)**: Single-file application with the following key functions:

- `get_redis_client()`: Creates Redis connections with TLS support
- `parse_response()`: Parses Redis INFO command output into Python dictionaries
- `process_node()`: Async function that collects metrics from individual Redis nodes over time
- `process_database()`: Orchestrates metric collection for entire database/cluster
- `main()`: CLI entry point with argument parsing

### Key Features

**Multi-Database Support**: Processes multiple Redis databases defined in config.ini sections

**Cluster Discovery**: Automatically discovers all cluster nodes from a single connection point

**Async Processing**: Uses asyncio for parallel node processing and progress tracking

**TLS Support**: Full TLS/SSL support with client certificates

**Comprehensive Metrics**: Tracks commands by type (Get, Set, Hash, List, etc.) and calculates precise throughput

### Configuration

**config.ini format**: Each database is a separate section with connection parameters:
- host, port, username, password
- TLS settings: tls, ca_cert, client_cert, client_key

**Output**: Excel workbook with detailed per-node metrics including memory usage, throughput, and command breakdowns

### Dependencies

- `redis`: Redis client library
- `openpyxl`: Excel file generation
- `tqdm`: Progress bars for async operations
- `configparser`: Configuration file parsing

## Important Notes

- Script requires Python 3.6+
- Non-intrusive: Does not affect Redis performance or data
- Best used during peak hours for accurate throughput measurements
- For clusters, only specify one node per cluster in config - script auto-discovers others