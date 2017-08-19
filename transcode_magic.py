#!/usr/bin/env python

from pymediainfo import MediaInfo
from subprocess import call
from time import sleep
import os
import argparse
import pickle

# Todo: add descriptions to arguments
parser = argparse.ArgumentParser(description='Automatically transcode files into h.264 with aac audio')
parser.add_argument('filename', nargs=1, help="Filename to process")
parser.add_argument('output',nargs='?', default=None, help="Optional output filename")
parser.add_argument('-n', '--no-copy', action='store_true', help="Do not remux if already in correct formats")
parser.add_argument('-i', '--in-place', action='store_true', help="Use the directory of the original as the destination")
parser.add_argument('-v', '--verbose', action='count', help="Verbosity")
parser.add_argument('-q', '--quiet', action='store_true', help="Quiets output from ffmpeg")
parser.add_argument('-l', '--log', action='store', help="Places some status information in specified logfile")
parser.add_argument('-f', '--force-video', action='store_true', help="Force video to be transcoded")
parser.add_argument('-a', '--force-audio', action='store_true', help="Force audio to be transcoded")
parser.add_argument('-d', '--debug', action='store', help="Dump pickled libmediainfo output to specified file and exit")

args = parser.parse_args()

# Copying out some of the arguments to simpler short variables
verbose = args.verbose
force_video = args.force_video
force_audio = args.force_audio
output_file = args.output

# Cache the full file and path for later (and easy reference)
full_filename = args.filename[0]

# Break down the filename for later modification
filename = os.path.basename(full_filename)

if verbose > 0:
    print(full_filename)

# Grab info from MediaInfo
media_info = MediaInfo.parse(full_filename)

# Preload basic command start for ffmpeg (later passed to subprocess.call)
command = ['/bin/nice', '-n' , '19', 'ionice', '-c3', '/bin/ffmpeg', '-i', full_filename]

# If quiet is specified, pass flags to tell ffmpeg to not produce output.
if args.quiet:
    command.extend(['-hide_banner','-loglevel','quiet'])

# If debug is used, it will dump the mediainfo data to a pickle file and stop.
if args.debug:
    with open(args.debug, 'w') as file:
        pickle.dump(media_info, file)
        exit(1)

# Default to true and correct later if a stream doesn't match the desired
# format. This way we can exit if user doesn't want to bother copying when
# already in the correct format.
straight_copy = True

# Iterate over each track, adding the appropriate copy/transcode commands based
# on content.
for track in media_info.tracks:
    if track.track_type == 'Video':
        if verbose > 1:
            print('Video ' + str(track.stream_identifier) + ': ' + track.format)
        command.extend(['-c:v:' + str(track.stream_identifier)])

        # AVC = h.264
        if track.format == 'AVC' and not force_video:
            command.append('copy')
        else:
            straight_copy = False
            command.extend(['libx264', '-crf', '18', '-tune', 'film', '-preset', 'veryfast'])

    elif track.track_type == 'Audio':
        command.append('-c:a:' + str(track.stream_identifier))
        if verbose > 1:
            print('Audio ' + str(track.stream_identifier) + ': ' + track.format)
        if track.format == 'AAC' and not force_audio:
            command.append('copy')
        else:
            straight_copy = False
            command.append('libfdk_aac')

    elif track.track_type == 'Text':
        # Since the destination format is mkv and I'm not partial to subtitle
        # format, just always copy subtitles.
        command.extend(['-c:s:' + str(track.stream_identifier), 'copy'])
        if verbose > 1:
            print('Captions ' + str(track.stream_identifier) + ': ' + track.format)

if args.no_copy and straight_copy:
    if verbose > 0:
        print("No transcoding needed. Exiting.")
    exit(0)

if output_file is None:
    orig_filename = filename

    # Sloppy swapping of file extensions.
    # Todo: clean up file extension swaps
    if filename[-4:].lower() != '.mkv':
        filename = filename[:-4] + '.mkv'

    # In place used for batch runs via find, so that bulk files can be transcoded.
    # Instead of copying to current directory, puts files in the source directory.
    if args.in_place:
        filename = os.path.split(full_filename)[0] + '/' + filename

    # Some basic effort to avoid name collisions. Primarily there to avoid trouble
    # if using in-place and the original is already in mkv format.
    if os.path.exists(filename):
        filename = filename[:-4] + '-new.mkv'
        if os.path.exists(filename):
            if verbose > 0:
                print("File already exists with -new modifier. Check for duplicate work and rename!")
            exit(0)
else:
    orig_filename = filename
    filename = output_file

# Strip excess metadata. See ffmpeg docs.
command.extend(['-map_metadata', '-1', filename]) 

# Print out command passed to call.
if verbose > 2:
    print(' '.join(command))

call(command)

# List completed files in log file, useful for tracking results of batch runs.
logfile = args.log

if not logfile is None:
    with open(logfile, 'a+') as log_file:
        log_file.write(orig_filename + '\n')
