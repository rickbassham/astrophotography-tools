#!/usr/bin/python

import argparse
import logging
import re
import signal
import subprocess
import socket
import os
import errno
import struct
import time

import functions

from threading import Event
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

SOLVE_FIELD_PATH = '/usr/local/bin/solve-field'

##############################
# Set up logging
##############################

FORMAT = '%(asctime)-15s %(levelname)-8s %(module)s %(lineno)d %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logger = logging.getLogger('encodeclient')

##############################
# Set up watching for CTRL-C
##############################

signal_event = Event()

def signal_handler(signal, frame):
    global signal_event
    logger.warning('You pressed Ctrl+C!')
    signal_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

##############################
# Utility functions
##############################

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


def solve(path, outputdir):
    command = [SOLVE_FIELD_PATH, '--overwrite', '--downsample', '8', '--depth', '1-40', '--plot-scale', '0.25', '--scale-high=2', '--dir', outputdir, path]

    logger.info(' '.join(command))

    try:
        p = subprocess.Popen(command, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        stdoutdata, stderrdata = p.communicate()

        if p.returncode != 0:
            logger.warning(stdoutdata)
            logger.warning(stderrdata)
            logger.warning('Unable to solve {0}'.format(path))
            return None
        else:
            match = re.search('^Field center: \(RA H:M:S, Dec D:M:S\) = \((.*), (.*)\).', stdoutdata, re.MULTILINE)

            if match is not None:
                ra = match.group(1)
                dec = match.group(2)

                logger.info('Solved {0} (RA, DEC) = ({1}, {2})'.format(path, ra, dec))

                return (ra, dec)
            else:
                logger.warning(stdoutdata)
                logger.warning(stderrdata)
                logger.warning('Unable to solve {0}'.format(path))
                return None

    except Exception as ex:
        logger.error(ex)
        return None


ra_str = None
dec_str = None

def main():
    global signal_event
    global ra_str
    global dec_str

    parser = argparse.ArgumentParser(description='Watches a folder for .jpg files and runs them through the astrometry.net solver.')

    parser.add_argument('--watch-folder', required=True, help="folder to watch for new jpg files (will be created if it does not exist)")
    parser.add_argument('--output-folder', required=True, help="folder to output solved information to (will be created if it does not exist)")

    args = parser.parse_args()

    watch_folder = args.watch_folder
    output_folder = args.output_folder

    mkdir_p(watch_folder)
    mkdir_p(output_folder)


    open_sockets = []

    # AF_INET means IPv4.
    # SOCK_STREAM means a TCP connection.
    # SOCK_DGRAM would mean an UDP "connection".
    listening_socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
    listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # The parameter is (host, port).
    # The host, when empty or when 0.0.0.0, means to accept connections for
    # all IP addresses of current machine. Otherwise, the socket will bind
    # itself only to one IP.
    # The port must greater than 1023 if you plan running this script as a
    # normal user. Ports below 1024 require root privileges.
    listening_socket.bind( ("", 10001) )

    # The parameter defines how many new connections can wait in queue.
    # Note that this is NOT the number of open connections (which has no limit).
    # Read listen(2) man page for more information.
    listening_socket.listen(5)
    listening_socket.setblocking(0)
    listening_socket.settimeout(0.5)

    def on_created(event):
        global ra_str
        global dec_str
        logger.info('Found new file: {0}'.format(event.src_path))

        # Sometimes we get the notification before the file is done being written. Wait half a second before processing.
        e = Event()
        e.wait(0.5)

        result = solve(event.src_path, output_folder)

        if result is not None:
            ra_str = result[0]
            dec_str = result[1]


    event_handler = PatternMatchingEventHandler(patterns=["*.jpg"])

    event_handler.on_created = on_created

    observer = Observer()
    observer.schedule(event_handler, watch_folder, recursive=True)
    observer.start()

    wait_time = 0.1

    while not signal_event.wait(wait_time):

        conn = None

        try:
            conn, addr = listening_socket.accept()
        except socket.timeout as ex:
            pass
        except socket.error as ex:
            if ex.errno == errno.EINTR:
                # CTRL-C was pressed. Ignore the error.
                pass
            else:
                logger.error(ex)
                raise

        if conn is not None:
            conn.setblocking(0)
            conn.settimeout(0.5)

            logger.info('Connected...')

            ra_str = None
            dec_str = None

            while not signal_event.wait(wait_time):

                if ra_str is not None and dec_str is not None:

                    ra_str = ra_str[0:ra_str.rfind('.')]
                    dec_str = dec_str[0:dec_str.rfind('.')]
                    dec_str = dec_str.replace('+', '')

                    ra = functions.hourStr_2_rad(ra_str)
                    dec = functions.degStr_2_rad(dec_str)

                    result = functions.rad_2_stellarium_protocol(ra, dec)

                    t = time.time() * 1000000

                    # 2 bytes integer - Length of message (24)
                    # 2 bytes integer - 0
                    # 8 bytes integer - microseconds since epoch
                    # 4 bytes unsigned integer - RA
                    # 4 bytes signed integer - DEC
                    # 4 bytes status - 0 == OK

                    packet = (24, 0, t, result[0], result[1], 0)

                    reply = struct.pack('<hhqIii', 24, 0, t, result[0], result[1], 0)
                    #print reply

                    for i in range(10):
                        conn.send(reply)

                    ra_str = None
                    dec_str = None

                data = None

                try:
                    # recv can throw socket.timeout
                    data = conn.recv(20)
                except socket.timeout as ex:
                    pass
                except socket.error as ex:
                    if ex.errno == errno.EINTR:
                        # CTRL-C was pressed. Ignore the error.
                        pass
                    else:
                        logger.error(ex)
                        raise

                if data is not None:
                    # 2 bytes integer - Length of message
                    # 2 bytes integer - 0
                    # 8 bytes integer - current time in microseconds since epoch
                    # 4 bytes unsigned integer - RA
                    # 4 bytes signed integer - DEC

                    data = struct.unpack("<hhqIi", data)

                    #print data
                    recieved_coords = functions.eCoords2str(data[3], data[4], data[2])

                    logger.info('Received slew command to (RA, DEC) = ({0}, {1})'.format(recieved_coords[0], recieved_coords[1]))

            logger.warning('Disconnected...')


if __name__ == "__main__":
    main()
