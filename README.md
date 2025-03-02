# Niri Recorder

Niri recorder is a shell script and waybar module to for creating screen recordings meant to be easily shared online.

### Dependencies

- `socat`
- `bash`
- `wf-recorder`
- `niri`
- `jq`
- `ffmpeg`
- `slurp`
- `python3` (optional)
- `waybar` (optional)
- `wl-clipboard`

## Recorder

A utility script meant to be triggered via keybinding. It will record your screen, then automatically compress the recording and copy its URI path to your clipboard, so you can easily paste it inside applications like Discord and Matrix. You do not need the Waybar module to use the script.

**Usage**:

`recorder.sh`

1. Run the script once to begin recording. Arguments:

- `screen` \[default]: record entire screen. Select screen if multi-monitor.
- `region`: Select a region to record.

2. Run the script again to stop recording.

- Arguments don't matter this time.
- Compression and copying to clipboard is done automatically.

## Waybar Module

There is an included waybar module. This module shows the current recording state. You can also use it to start/stop the recording with your mouse. Please see `recorder_config.jsonc` for an example of how to setup the custom module.

You can also use `test_waybar.sh` to test the module without creating any recordings. After you've loaded the Waybar module, simply run the script, and you should see the module responding to socket messages.

## Acknowledgments

- Thanks to [Axlefublr](https://axlefublr.github.io/screen-recording/) for the method to optimize the compression of the video.
