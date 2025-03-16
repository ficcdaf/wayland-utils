#!/bin/env bash

# depends: wf-recorder, libnotify

TEMPDIR="/tmp/niri-recorder"
mkdir -p "$TEMPDIR"
LOCK="$TEMPDIR/lock"
RFMT=".mkv"
OFMT=".mp4"
RAW="$TEMPDIR/raw$RFMT"
OUTDIR="$HOME/Videos/niri-recorder"
mkdir -p "$OUTDIR"

# sends current recording state to socket
function sig {
  echo "$1" | socat - UNIX-CONNECT:/tmp/recorder-sock.sock
}

# function generates unique name for recording
function compname {
  now=$(date +"%y-%m-%d-%H:%M:%S")
  echo "$OUTDIR/$now$OFMT"
}

# First we need to check if the recording
# lockfile exists.
if [[ -f "$LOCK" ]]; then
  # Stop the recording
  sig "STP"
  kill "$(cat "$LOCK")"
  # remove lockfile
  rm "$LOCK"
  outpath="$(compname)"
  sig "CMP"
  # compress the recording
  ffmpeg -y -i "$RAW" -c:v libx264 -preset slow -crf 21 -r 30 -b:v 2M -maxrate 3M -bufsize 4M -c:a aac -b:a 96k -movflags +faststart "$outpath" || (sig "ERR"; exit 1)
  # copy URI path to clipboard
  wl-copy -t 'text/uri-list' <<<"file://$outpath" || (sig "ERR"; exit 1)
  sig "CPD"
  # delete the raw recording
  rm "$RAW"

else
  # count how many monitors are attached
  num_mon=$(niri msg --json outputs | jq 'keys | length')
  wf_flags="-Dyf"
  if [ "$1" = "region" ];then
    # select a screen region
    sel=$(slurp) || exit 1
    wf-recorder -g "$sel" "$wf_flags" "$RAW" &
  elif [ "$1" = "screen" ] || [ "$1" = "" ] && (( num_mon > 1 )); then
    # select entire screen
    sel=$(slurp -o) || exit 1
    wf-recorder -g "$sel" "$wf_flags" "$RAW" &
  else
    # this runs when screen is specified and there's only one monitor
    # it also runs with no args bc screen is default
    wf-recorder "$wf_flags" "$RAW" &
  fi

  sig "REC"
  # create lockfile
  touch "$LOCK"

  # save recorder's process id to lockfile
  PID=$!
  echo "$PID" > "$LOCK"
fi

