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
echo "--------------------------"
for (( c=1; c<=10000; c++ ))
do
    cat << EOF | redis-cli -h $HOST -p $PORT > /dev/null
SETBIT bit$c $c 1
GETBIT bit$c $c
EVAL "return ARGV[1]" 0 $c
GEOADD Sicily 13.361389 38.115556 Palermo 15.087269 37.502669 Catania
GEORADIUS Sicily 15 37 100 km
HSET hash$c number $c
HGET hash$c number
PFADD hyperloglog$c a b c d e f g
PFCOUNT hyperloglog$c
EXISTS string$c
EXISTS nostring$c
lpush list$c $c
rpop list$c
PUBLISH channel message$c
SADD set$c item$c
SMEMBERS set$c
ZADD zset$c $c item
ZRANGE  zset$c 0 -1 WITHSCORES
SET string$c $c
GET string$c
XLEN mystream$c
UNWATCH
EOF

    echo -ne "Iteration: $c"\\r    
    sleep 0.0001
done

echo ""
echo "--------------------------"
echo "Done!"
