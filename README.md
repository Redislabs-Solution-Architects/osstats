# OSStats

TBD


## Installation

The script will run on any system with Python 3.6 or greater installed.

### Running the script from source

Download the repository

```
git clone https://github.com/Redislabs-Solution-Architects/osstats && cd osstats
```

Prepare and activate the virtual environment

```
python3 -m venv .env && source .env/bin/activate
```

Install necessary libraries and dependencies

```
pip install -r requirements.txt
```

Copy the example configuration file and update its contents to match your configuration:

```
cp config.ini.example config.ini && vim config.ini
```

Execute 

```
python osstats.py
```

When finished do not forget to deactivate the virtual environment

```
deactivate
```