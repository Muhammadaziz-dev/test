#!/usr/bin/env bash
# wait-for-it.sh

HOST=$1
PORT=$2
shift 2
CMD="$@"

echo "Waiting for $HOST:$PORT..."
until nc -z "$HOST" "$PORT"; do
  sleep 1
done

>&2 echo "$HOST:$PORT is available, executing command..."
exec $CMD
