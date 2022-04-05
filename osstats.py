# -*- coding: utf-8 -*-

import os
import sys
import argparse
import configparser
import redis
import openpyxl
import asyncio
from tqdm.asyncio import trange


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

async def sleep(duration):
    await asyncio.sleep(duration)
    
async def progress(duration):
    duration = duration * 60
    for i in trange(duration):
        await asyncio.sleep(1)
    

async def process_node(config, node, is_master_shard, duration):
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
    print("Processing node {}:{}".format(params[0], params[1]))

    client = get_redis_client(
        params[0], 
        params[1], 
        config['password'], 
        config['username'], 
        config['tls']
    )

    result = {}

    # first run
    res1 = parse_response(client.execute_command('info commandstats'))
    info1 = client.execute_command('info')
    await sleep(duration * 60)

    # second run
    res2 = parse_response(client.execute_command('info commandstats'))
    info2 = client.execute_command('info')

    duration_in_seconds = 60 * duration

    result['Source'] = 'oss'
    result['DB Name'] = params[0].replace('.', '-')
    result['Redis Version'] = info2['redis_version']
    result['OS'] = info2['os']
    result['BytesUsedForCache'] = info2['used_memory_peak']
    result['Memory Limit (GB)'] = round(info2['used_memory_peak'] / 1024 ** 3, 3)
    result['CurrConnections'] = info2['connected_clients']
    result['cluster_enabled'] = info2['cluster_enabled']
    result['Node Type'] = 'Master' if is_master_shard else 'Replica'
    result['connected_slaves'] = info2['connected_slaves'] \
        if 'connected_slaves' in info2 else ''
    result['TotalOps'] = (info2['total_commands_processed'] - info1['total_commands_processed']) / duration_in_seconds

    # Bitmaps based commands
    result['BitmapBasedCmds'] = round(get_command_by_args(
        res1, 
        res2, 
        'bitcount',
        'bitfield',
        'bitfield_ro',
        'bitop',
        'bitpos',
        'getbit',
        'setbit'
    ) / duration_in_seconds)

    # String based commands
    result['ClusterBasedCmds'] = round(get_command_by_args(
        res1, 
        res2, 
        'asking',
        'cluster'
    ) / duration_in_seconds)

    # Eval based commands
    result['EvalBasedCmds'] = round(get_command_by_args(
        res1,
        res2,
        'eval',
        'evalsha',
        'evalsha_ro',
        'eval_ro',
        'fcall',
        'fcall_ro',
        'function',
        'script'
    ) / duration_in_seconds)

    # GeoSpatial based commands
    result['GeoSpatialBasedCmds'] = round(get_command_by_args(
        res1, 
        res2, 
        'geoadd',
        'geodist',
        'geohash',
        'geopos',
        'georadius',
        'georadiusbymember',
        'georadiusbymember_ro',
        'georadius_ro',
        'geosearch',
        'geosearchstore'
    ) / duration_in_seconds)

    # Hash based commands
    result['HashBasedCmds'] = round(get_command_by_args(
        res1, 
        res2, 
        'hdel',
        'hexists',
        'hget',
        'hgetall',
        'hincrby',
        'hincrbyfloat',
        'hkeys',
        'hlen',
        'hmget',
        'hmset',
        'hrandfield',
        'hscan',
        'hset',
        'hsetnx',
        'hstrlen',
        'hvals'
    ) / duration_in_seconds)

    # HyperLogLog based commands
    result['HyperLogLogBasedCmds'] = round(get_command_by_args(
        res1, 
        res2, 
        'pfadd',
        'pfcount',
        'pfdebug',
        'pfmerge',
        'pfselftest'
    ) / duration_in_seconds)

    # Keys based commands
    result['KeyBasedCmds'] = round(get_command_by_args(
        res1, 
        res2, 
        'copy',
        'del',
        'dump',
        'exists',
        'expire',
        'expireat',
        'expiretime',
        'keys',
        'migrate',
        'move',
        'object',
        'persist',
        'pexpire',
        'pexpireat',
        'pexpiretime',
        'pttl',
        'randomkey',
        'rename',
        'renamenx',
        'restore',
        'scan',
        'sort',
        'sort_ro',
        'touch',
        'ttl',
        'type',
        'unlink',
        'wait'
    ) / duration_in_seconds)

    # List based commands
    result['ListBasedCmds'] = round(get_command_by_args(
        res1,
        res2,
        'blmove',
        'blmpop',
        'blpop',
        'brpop',
        'brpoplpush',
        'lindex',
        'linsert',
        'llen',
        'lmove',
        'lmpop',
        'lpop',
        'lpos',
        'lpush',
        'lpushx',
        'lrange',
        'lrem',
        'lset',
        'ltrim',
        'rpop',
        'rpoplpush',
        'rpush',
        'rpushx'    
    ) / duration_in_seconds)

    # PubSub based commands
    result['PubSubBasedCmds'] = round(get_command_by_args(
        res1,
        res2,
        'psubscribe',
        'publish',
        'pubsub',
        'punsubscribe',
        'spublish',
        'ssubscribe',
        'subscribe',
        'sunsubscribe',
        'unsubscribe'
    ) / duration_in_seconds)

    # Sets based commands
    result['SetBasedCmds'] = round(get_command_by_args(
        res1, 
        res2, 
        'sadd',
        'scard',
        'sdiff',
        'sdiffstore',
        'sinter',
        'sintercard',
        'sinterstore',
        'sismember',
        'smembers',
        'smismember',
        'smove',
        'spop',
        'srandmember',
        'srem',
        'sscan',
        'sunion',
        'sunionstore'
    ) / duration_in_seconds)

    # SortedSets based commands
    result['SortedSetBasedCmds'] = round(get_command_by_args(
        res1, 
        res2, 
        'bzmpop',
        'bzpopmax',
        'bzpopmin',
        'zadd',
        'zcard',
        'zcount',
        'zdiff',
        'zdiffstore',
        'zincrby',
        'zinter',
        'zintercard',
        'zinterstore',
        'zlexcount',
        'zmpop',
        'zmscore',
        'zpopmax',
        'zpopmin',
        'zrandmember',
        'zrange',
        'zrangebylex',
        'zrangebyscore',
        'zrangestore',
        'zrank',
        'zrem',
        'zremrangebylex',
        'zremrangebyrank',
        'zremrangebyscore',
        'zrevrange',
        'zrevrangebylex',
        'zrevrangebyscore',
        'zrevrank',
        'zscan',
        'zscore',
        'zunion',
        'zunionstore'
    ) / duration_in_seconds)

    # String based commands
    result['StringBasedCmds'] = round(get_command_by_args(
        res1, 
        res2, 
        'append',
        'decr',
        'decrby',
        'get',
        'getdel',
        'getex',
        'getrange',
        'getset',
        'incr',
        'incrby',
        'incrbyfloat',
        'lcs',
        'mget',
        'mset',
        'msetnx',
        'psetex',
        'set',
        'setex',
        'setnx',
        'setrange',
        'strlen',
        'substr'
    ) / duration_in_seconds)

    # Stream based commands
    result['StreamBasedCmds'] = round(get_command_by_args(
        res1,
        res2,
        'xack',
        'xadd',
        'xautoclaim',
        'xclaim',
        'xdel',
        'xgroup',
        'xinfo',
        'xlen',
        'xpending',
        'xrange',
        'xread',
        'xreadgroup',
        'xrevrange',
        'xsetid',
        'xtrim'
    ) / duration_in_seconds)
    
    # Transaction based commands
    result['TransactionBasedCmds'] = round(get_command_by_args(
        res1,
        res2,
        'discard',
        'exec',
        'multi',
        'unwatch',
        'watch'
    ) / duration_in_seconds)
    
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

async def run_tasks(tasks):
    res = await asyncio.gather(*tasks)
    return res


def process_database(config, section, workbook, duration,loop):

    print("\nConnecting to {} database ..".format(section))

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
    
    # Process Redis nodes in parallel
   
    tasks = []
    for node, stats in nodes.items():
        is_master_shard = False
        if stats['flags'].find('master') >= 0:
            is_master_shard = True
        if stats['connected'] is True:
            tasks.append(
                loop.create_task(
                    process_node(config, node, is_master_shard, duration)
                )
            )
    tasks.append(
        loop.create_task(
            progress(duration)
        )
    )
    results = loop.run_until_complete(run_tasks(tasks))

    for result in results:
        node_stats = result
        if node_stats is not None:
            if ws.max_row == 1:
                ws.append(list(node_stats.keys()))    
            ws.append(list(node_stats.values()))

   
    # End
    
    return workbook


def main():
    if not sys.version_info >= (3, 6):
        print("Please upgrade python to a version at least 3.6")
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", 
        "--config", 
        dest="configFile",
        default="config.ini",        
        help="The filename for configuration file. By default the script will try to open the config.ini file.", 
        metavar="FILE"
    )    
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
    
    if args.duration < 1:
        print("Invalid duration specified. Please specify a valid duration time in minutes".format(args.configFile))
        sys.exit(1)
    
    # Open and parse the configuration file.
    config = configparser.ConfigParser()
    config.read(args.configFile)
    
    print("The output will be stored in {}".format(args.outputFile))

    wb = create_workbook()
    loop = asyncio.get_event_loop()
    for section in config.sections():
        wb = process_database(dict(config.items(section)), section, wb, 1,loop)
    loop.close()
    print("\nWriting output file {}".format(args.outputFile))
    wb.save(args.outputFile)
    print("Done!")

if __name__ == "__main__":
    main()
