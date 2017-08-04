#!/bin/python

from pymediainfo import MediaInfo
from subprocess import call
from time import sleep
import os
import argparse
import pickle

parser = argparse.ArgumentParser(description='Automatically transcode files into h.264 with aac audio')
parser.add_argument('filename', nargs=1)
parser.add_argument('-n', '--no-copy', action='store_true')
parser.add_argument('-i', '--in-place', action='store_true')
parser.add_argument('-v', '--verbose', action='count')
parser.add_argument('-l', '--log', action='store')
parser.add_argument('-f', '--force-video', action='store_true')
parser.add_argument('-a', '--force-audio', action='store_true')
parser.add_argument('-d', '--debug', action='store')

args = parser.parse_args()

verbose = args.verbose
force_video = args.force_video
force_audio = args.force_audio

full_filename = args.filename[0]
filename = os.path.basename(full_filename)

if verbose > 0:
    print(full_filename)

media_info = MediaInfo.parse(full_filename)
command = ['/bin/nice', '-n' , '19', '/bin/ffmpeg', '-i', full_filename]

if args.debug:
    with open(args.debug, 'w') as file:
        pickle.dump(media_info, file)
        exit(1)

straight_copy = True

for track in media_info.tracks:
    if track.track_type == 'Video':
        if verbose > 1:
            print('Video ' + str(track.stream_identifier) + ': ' + track.format)
        command.extend(['-c:v:' + str(track.stream_identifier)])
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
        command.extend(['-c:s:' + str(track.stream_identifier), 'copy'])
        if verbose > 1:
            print('Captions ' + str(track.stream_identifier) + ': ' + track.format)

if args.no_copy and straight_copy:
    if verbose > 0:
        print("No transcoding needed. Exiting.")
    exit(0)

orig_filename = filename

if filename[-4:].lower() != '.mkv':
    filename = filename[:-4] + '.mkv'

if args.in_place:
    filename = os.path.split(full_filename)[0] + '/' + filename

if os.path.exists(filename):
    filename = filename[:-4] + '-new.mkv'
    if os.path.exists(filename):
        if verbose > 0:
            print("File already exists with -new modifier. Check for duplicate work and rename!")
        exit(0)

command.extend(['-map_metadata', '-1', filename]) 

if verbose > 2:
    print(' '.join(command))

call(command)

logfile = args.log

if not logfile is None:
    with open(logfile, 'a+') as log_file:
        log_file.write(orig_filename + '\n')
