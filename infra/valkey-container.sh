#!/bin/sh
set -eu
umask 077
{
  printf '%s\n' 'bind 0.0.0.0' 'port 6379' 'protected-mode yes' 'dir /data' \
    'appendonly yes' 'appendfsync everysec' 'maxmemory 128mb' 'maxmemory-policy noeviction'
  printf 'requirepass '
  cat /run/secrets/broker_password
  printf '\n'
} > /tmp/resolveflow-valkey.conf
exec valkey-server /tmp/resolveflow-valkey.conf
