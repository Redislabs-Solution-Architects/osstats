# -*- coding: utf-8 -*-

import os
import sys
import argparse
import configparser
import redis
import openpyxl
import concurrent.futures
import time


def get_value(value):
    if ',' not in value or '=' not in value:
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return value
    else:
        sub_dict = {}
        for item in value.split(','):
            k, v = item.rsplit('=', 1)
            sub_dict[k] = get_value(v)
        return sub_dict


def native_str(x):
    return x if isinstance(x, str) else x.decode('utf-8', 'replace')


def parse_response(response):
    """
        Parse the result of Redis's INFO command into a Python dict
        Args:
            response: the response from the info command
        Returns:
            command stats output
    """
    res = {}
    response = native_str(response)

    for line in response.splitlines():
        if line and not line.startswith('#'):
            if line.find(':') != -1:
                # Split, the info fields keys and values.
                # Note that the value may contain ':'. but the 'host:'
                # pseudo-command is the only case where the key contains ':'
                key, value = line.split(':', 1)
                if key == 'cmdstat_host':
                    key, value = line.rsplit(':', 1)
                res[key] = get_value(value)
            else:
                # if the line isn't splittable, append it to the "__raw__" key
                res.setdefault('__raw__', []).append(line)

    return res


def get_cmd_metrics():
    metrics = [
        'HashBasedCmds',
        'HyperLogLogBasedCmds',
        'KeyBasedCmds',
        'ListBasedCmds',
        'SetBasedCmds',
        'SortedSetBasedCmds',
        'StringBasedCmds',
        'StreamBasedCmds',
        'TotalOps']
    return metrics


def get_metrics():
    metrics = [
        'CurrItems',
        'BytesUsedForCache',
        'CurrConnections',
        'cluster_enabled',
        'connected_slaves',
        'duration',
        'Memory Limit (GB)']
    return metrics


def create_workbook():
    """Create an empty workbook with headers
    Args:
    Returns:
    The newely created pandas dataframe
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Raw Input Data'

    return wb        


def get_command_by_args(cmds1, cmds2, *args):
    count = 0
    for cmd in args:
        command = 'cmdstat_%s' % cmd
        try:
            count += cmds2[command]['calls'] - cmds1[command]['calls']
        except KeyError:
            pass
    return count


def get_redis_client(host, port, password, username, tls):
    if not password:
        client = redis.Redis(
            host = host,
            port = port,
            socket_timeout = 10,
            decode_responses=True,
            ssl = False if not tls else True
        )
    else:
        if not username:
            client = redis.Redis(
                host = host,
                port = port,
                password = password,
                socket_timeout = 10,
                decode_responses=True,
                ssl = False if not tls else True
            )   
        else:
            client = redis.Redis(
                host = host,
                port = port,
                username = username,
                password = password,
                socket_timeout = 10,
                decode_responses=True,
                ssl = False if not tls else True
            )
    return client


def process_node(config, node, is_master_shard, duration):
    """
        Get the current command stats of the passed node
        Args:
            row: a row from the input file
            node: the node to be processed
            is_master_shard: is master shard
            duration: the duration between runs
        Returns:
            command stats output
    """
    params = node.split(':')

    client = get_redis_client(
        params[0], 
        params[1], 
        config['password'], 
        config['username'], 
        config['tls']
    )

    print("Processing node {}:{}".format(params[0], params[1]))
    result = {}

    # first run
    res1 = parse_response(client.execute_command('info commandstats'))
    info1 = client.execute_command('info')
    time.sleep(duration * 60)

    # second run
    res2 = parse_response(client.execute_command('info commandstats'))
    info2 = client.execute_command('info')

    result['Source'] = 'oss'
    result['DB Name'] = params[0].replace('.', '-')
    result['Redis Version'] = info2['redis_version']
    result['BytesUsedForCache'] = info2['used_memory_peak']
    result['Memory Limit (GB)'] = info2['used_memory_peak'] / 1024 ** 3
    result['CurrConnections'] = info2['connected_clients']
    result['cluster_enabled'] = info2['cluster_enabled']

    result['Node Type'] = 'Master' if is_master_shard else 'Replica'
    result['connected_slaves'] = info2['connected_slaves'] \
        if 'connected_slaves' in info2 else ''
    result['duration'] = 60 * duration
    result['TotalOps'] = info2['total_commands_processed'] - \
        info1['total_commands_processed']

    # String
    result['StringBasedCmds'] = get_command_by_args(
        res1, 
        res2, 
        'get', 
        'set', 
        'incr', 
        'decr', 
        'incrby', 
        'decrby'
    )

    # Hash
    result['HashBasedCmds'] = get_command_by_args(
        res1, 
        res2, 
        'hget', 
        'hset', 
        'hgetall', 
        'hmget', 
        'hsetnx'
    )

    # HyperLogLog
    result['HyperLogLogBasedCmds'] = get_command_by_args(
        res1, 
        res2, 
        'pfadd', 
        'pfcount', 
        'pfmerge'
    )

    # Keys
    result['KeyBasedCmds'] = get_command_by_args(
        res1, 
        res2, 
        'del', 
        'expire', 
        'unlink'
    )

    # List
    result['ListBasedCmds'] = get_command_by_args(
        res1,
        res2,
        'blpop',
        'brpop',
        'brpoplpush',
        'blmove',
        'linsert',
        'llen',
        'lpop',
        'lpush',
        'lpushx',
        'lrange',
        'lset',
        'lrem',
        'rpop',
        'rpoplpush',
        'rpush',
        'rpushx'
    )

    # Sets
    result['SetBasedCmds'] = get_command_by_args(
        res1, 
        res2, 
        'sadd', 
        'scard', 
        'sdiff', 
        'sdiffstore', 
        'sinter',
        'sinterstore', 
        'sismember', 
        'smismember', 
        'smembers', 
        'smove', 
        'spop',
        'srandmember', 
        'srem', 
        'sunion', 
        'sunionstore', 
        'sscan'
    )

    # SortedSets
    result['SortedSetBasedCmds'] = get_command_by_args(
        res1, 
        res2, 
        'bzpopmin', 
        'bzpopmax', 
        'zadd', 
        'zcard', 
        'zcount',
        'zdiff', 
        'zdiffstore', 
        'zincrby', 
        'zinter', 
        'zinterstore',
        'zlexcount', 
        'zpopmax', 
        'zpopmin', 
        'zrange', 
        'zrangebylex',
        'zrevrangebylex', 
        'zrangebyscore', 
        'zrank', 
        'zrem',
        'zremrangebylex', 
        'zremrangebyrank', 
        'zremrangebyscore',
        'zrevrange', 
        'zrevrangebyscore', 
        'zrevrank', 
        'zscore', 
        'zunion',
        'zmscore', 
        'zunionstore', 
        'zscan'
    )

    # Streams
    result['StreamBasedCmds'] = get_command_by_args(
        res1,
        res2,
        'xadd',
        'xtrim',
        'xdel',
        'xrange',
        'xrevrange',
        'xlen',
        'xread',
        'xgroup',
        'xreadgroup',
        'xack',
        'xclaim',
        'xpending'
    )
    
    result['CurrItems'] = 0
    result['Namespaces'] = ""
    for x in range(16):
        db = "db{}".format(x)
        if db in info2:
            # debug('num of keys %s' % info2[db]['keys'])
            result['CurrItems'] += info2[db]['keys']
            if x > 0:
                result['Namespaces'] += ", "    
            result['Namespaces'] += f"{db}:{info2[db]['keys']}"

    return result


# Capture Version of Redis
def process_database(config, section, workbook, duration):

    print("Connecting to {} database ..".format(section))

    client = get_redis_client(
        config['host'], 
        config['port'], 
        config['password'], 
        config['username'], 
        config['tls']
    )

    try:
        client.ping()
        print("Connected to {} database".format(section))
    except BaseException:
        print("Error connecting to {} database".format(section))
        return workbook

    info = client.execute_command('info')
    if 'cluster_enabled' in info and info['cluster_enabled'] == 1:
        nodes = client.execute_command('cluster nodes')
    else:
        nodes = {
            '%s:%s' % (config['host'], config['port']): {'flags': 'master', 'connected': True}
        }

    ws = workbook.active
    
    with concurrent.futures.ProcessPoolExecutor():
        for node, stats in nodes.items():
            is_master_shard = False
            if stats['flags'].find('master') >= 0:
                is_master_shard = True

            if stats['connected'] is True:
                node_stats = process_node(config, node, is_master_shard, duration)
                if ws.max_row == 1:
                    ws.append(list(node_stats.keys()))    
                ws.append(list(node_stats.values()))
    
    return workbook


def main():
    if not sys.version_info >= (3, 6):
        print("Please upgrade python to a version at least 3.6".format(args.configFile))
        exit(1)


    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", 
        "--config", 
        dest="configFile",
        default="config.ini",        
        help="The filename for configuration file. By default the script will try to open the config.ini file.", 
        metavar="FILE"
    )    
    # parser.add_argument(
    #     "inputFile",
    #     help = "The Excel file containing Redis endpoints to pull stats from"
    # )
    parser.add_argument(
        "-d",
        "--duration",
        type = int,
        help = "Period in minutes between gathering data from the endpoint",
        default = 5
    )
    parser.add_argument(
        "-o",
        "--output-file",
        dest="outputFile",
        default="OssStats.xlsx",
        help = "Name of file results are written to. Defaults to OssStats.xlsx"
    )
    args = parser.parse_args()

    if not os.path.isfile(args.configFile):
        print("Can't find the specified {} configuration file".format(args.configFile))
        sys.exit(1)
    
    # Open and parse the configuration file.
    config = configparser.ConfigParser()
    config.read(args.configFile)
    
    print("The output will be stored in {}".format(args.outputFile))

    wb = create_workbook()

    for section in config.sections():
        wb = process_database(dict(config.items(section)), section, wb, args.duration)

    print("Writing output file {}".format(args.outputFile))
    wb.save(args.outputFile)
    print("Done!")

if __name__ == "__main__":
    main()
