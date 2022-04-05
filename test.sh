#!/bin/bash
clear

HOST=127.0.0.1
PORT=6379

echo ""
echo "Input to ECache"
echo "------------------------"
echo ""
echo "Details"
echo "-------"
echo "Host      : $HOST"
echo "Port      : $PORT"
echo ""
echo "Counting nb of increments:"
echo "-----------------------"
for (( c=1; c<=12000000; c++ ))
do
    redis-cli -h $HOST -p $PORT -c SETBIT bit$c $c 1 > /dev/null
    redis-cli -h $HOST -p $PORT -c GETBIT bit$c $c > /dev/null
    redis-cli -h $HOST -p $PORT -c EVAL "return ARGV[1]" 0 $c > /dev/null
    redis-cli -h $HOST -p $PORT -c GEOADD Sicily 13.361389 38.115556 Palermo 15.087269 37.502669 Catania > /dev/null
    redis-cli -h $HOST -p $PORT -c GEORADIUS Sicily 15 37 100 km > /dev/null
    redis-cli -h $HOST -p $PORT -c HSET hash$c number $c > /dev/null
    redis-cli -h $HOST -p $PORT -c HGET hash$c number > /dev/null
    redis-cli -h $HOST -p $PORT -c PFADD hyperloglog$c a b c d e f g > /dev/null
    redis-cli -h $HOST -p $PORT -c PFCOUNT hyperloglog$c > /dev/null
    redis-cli -h $HOST -p $PORT -c EXISTS string$c > /dev/null
    redis-cli -h $HOST -p $PORT -c EXISTS nostring$c > /dev/null
    redis-cli -h $HOST -p $PORT -c lpush list$c $c > /dev/null
    redis-cli -h $HOST -p $PORT -c rpop list$c > /dev/null
    redis-cli -h $HOST -p $PORT -c PUBLISH channel message$c > /dev/null
    redis-cli -h $HOST -p $PORT -c SADD set$c item$c > /dev/null
    redis-cli -h $HOST -p $PORT -c SMEMBERS set$c > /dev/null
    redis-cli -h $HOST -p $PORT -c ZADD zset$c $c item > /dev/null
    redis-cli -h $HOST -p $PORT -c ZRANGE  zset$c 0 -1 WITHSCORES > /dev/null
    redis-cli -h $HOST -p $PORT -c SET string$c $c > /dev/null
    redis-cli -h $HOST -p $PORT -c GET string$c > /dev/null
    redis-cli -h $HOST -p $PORT -c XLEN mystream$c > /dev/null
    redis-cli -h $HOST -p $PORT -c UNWATCH  > /dev/null
   echo "iteration $c"
   echo "-----"
   sleep 0.0001
done