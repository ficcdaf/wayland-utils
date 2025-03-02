#!/bin/env bash

echo "REC" | socat - UNIX-CONNECT:/tmp/recorder-sock.sock; \
sleep 2; \
echo "ERR" | socat - UNIX-CONNECT:/tmp/recorder-sock.sock; \
sleep 2; \
echo "REC" | socat - UNIX-CONNECT:/tmp/recorder-sock.sock; \
sleep 2; \
echo "STP" | socat - UNIX-CONNECT:/tmp/recorder-sock.sock; \
sleep 2; \
echo "CMP" | socat - UNIX-CONNECT:/tmp/recorder-sock.sock; \
sleep 2; \
echo "CPD" | socat - UNIX-CONNECT:/tmp/recorder-sock.sock; \
sleep 2; 
