# OSStats

OSStats is a tool for extracting Redis database metrics. The script is able to process multiple Redis databases, both single instance and clustered ones. 

The script will automatically parse all the Redis databases defined in the configuration file. It will connect to the Redis databases and it will run an INFO and an INFO COMMANDSTATS command. It will wait for a predifined period (5 minutes by default) and it will run the above commands one more time. It will then subtract the command metrics and it will calculate a precise estimate for the throughput the database is getting at the time the script is running. It is highly recommended to use the script during pick hours for getting more reliable results. 

This script by no means will affect the performance and the data stored in the Redis databases it is scanning.


## Installation

There are couple of ways to run the script which are mentioned as below:

### 1. Running the script from source

**Pre-requisites:** The script will run on any system with Python 3.6 or greater installed. 

Download the repository

```
# git clone https://github.com/Redislabs-Solution-Architects/osstats && cd osstats
```

Prepare and activate the virtual environment

```
# python3 -m venv .env && source .env/bin/activate
```

Install necessary libraries and dependencies

```
# pip install -r requirements.txt
```

Copy the example configuration file and update its contents to match your configuration. Multiple Redis databases can be defined in this files and the script will process all the databases that are defined as separate sections in the config.ini file.

For any clustered Redis database it is important to mention that only a single node of the cluster needs to be defined in the config.ini and not all the nodes. The script will query the node and it will discover all the participating cluster nodes automatically.

```
# cp config.ini.example config.ini && vim config.ini
```

Execute the script. Use the -d option to change the duration in minutes the script will wait for running the second set of INFO and INFO COMMANDSTATS commands. By default this flag is set to 5 minutes.

By default, the output will be stored in OSStats.xlsx. Use -c option to change the name of output file.

```
# python osstats.py
```

When finished do not forget to deactivate the virtual environment

```
# deactivate
```


### 2. Running the script from Docker image

**Pre-requisites:** You have Docker engine installed on your machine. Refer this link to install Docker engine: `https://docs.docker.com/engine/install/`


Download the repository

```
# git clone https://github.com/Redislabs-Solution-Architects/osstats && cd osstats
```

Copy the example configuration file and update its contents to match your configuration. Multiple Redis databases can be defined in this files and the script will process all the databases that are defined as separate sections in the config.ini file.

For any clustered Redis database it is important to mention that only a single node of the cluster needs to be defined in the config.ini and not all the nodes. The script will query the node and it will discover all the participating cluster nodes automatically.

```
# cp config.ini.example config.ini && vim config.ini
```

Execute the script using `docker run` command. Use the -d option to change the duration in minutes the script will wait for running the second set of INFO and INFO COMMANDSTATS commands. By default this flag is set to 5 minutes.

By default, the output will be stored in OSStats.xlsx. Use -c option to change the name of output file.

```
# pwd
```
For example, output of this command is `/a/path/to/osstats`. Use the below docker command to run the script

```
# docker run -v /a/path/to/osstats:/app -t sumitshatwara/redis-osstats python3 osstats.py
```


