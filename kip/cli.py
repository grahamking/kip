#!/usr/bin/env python3
""" kip: Keep Internet Passwords.

kip is a command line tool to storing usernames and passwords
 in gnupg-encrypted text files.

It is intended as an alternative to onepassword, keepass, etc.
Run it for more details.
---

Copyright 2011 Graham King

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

For full license details see <http://www.gnu.org/licenses/>.
"""

# pylint doesn't like python3's built-in 'input'
# pylint: disable=W0141

import os
import os.path
try:
    import configparser
except ImportError:
    # Python 2
    import ConfigParser as configparser
import sys
import random
import string                                           # pylint: disable=W0402
import subprocess
import glob

from kip import __version__

NAME = sys.argv[0]

config = configparser.ConfigParser()
config.read(
        [
            os.path.join(os.path.dirname(__file__), "kip.conf"),
            os.path.expanduser('~/.kip/kip.conf')
        ])

HOME_PWD = os.path.expanduser(config.get('passwords', 'home'))
LEN_PWD = int(config.get('passwords', 'len'))
ENCRYPT_CMD = config.get('gnupg', 'encrypt_cmd')
DECRYPT_CMD = config.get('gnupg', 'decrypt_cmd')

USAGE = """
v{version}
{name} manages accounts details in gpg files.

Usage:

 $ {name} ebay.com
 Decrypts {home}ebay.com using gpg
 Copies password (first line) to clipboard
 Echoes ebay username and notes (other lines)

 $ {name} ebay.com graham_king "And some notes"
 Generate random password (pwgen -s1 19)
 Creates file {home}ebay.com with format:
    pw
    username
    notes
 Encrypts and signs it with gpg.

 $ echo "S3cret" | {name} ebay.com graham_king "Notes"
 $ pwgen -s1 19 | {name} ebay.com graham_king "Notes"
 If there is a pipe input, use that as the password, instead
 of randomly generating.

 If the LAST argument is --print output pw to stdout instead of
 using xclip. This is useful if you're on a headless machine, but
 check over your shoulder first!

""".format(name=NAME, home=HOME_PWD + os.path.sep, version=__version__)

TEMPLATE = """{password}
{username}
{notes}"""
if sys.platform == 'darwin':
    CLIP_CMD = 'pbcopy'
else:
    CLIP_CMD = 'xclip'


def main(argv=None):
    """Start here"""
    if not argv:
        argv = sys.argv

    if len(argv) == 1:
        print(USAGE)
        return 1

    # Ensure our home directory exists
    if not os.path.exists(HOME_PWD):
        os.makedirs(HOME_PWD)

    is_visible = (argv[len(argv) - 1] == '--print')

    if len(argv) == 2 or is_visible:
        retcode = show(argv[1], is_visible)
    else:
        retcode = create(*argv[1:])

    return retcode


def create(name, username, notes=None, **kwargs):
    """Create a new entry"""
    if 'pwd' in kwargs:
        password = kwargs['pwd']
    elif not sys.stdin.isatty():
        # stdin is a pipe
        password = sys.stdin.read().strip()
    else:
        # No pw given, make random one
        password = pwgen(LEN_PWD)

    if not notes:
        notes = ''

    file_contents = TEMPLATE.format(
        password=password,
        username=username,
        notes=notes)
    enc = encrypt(file_contents)

    dest_filename = os.path.join(HOME_PWD, name)
    if os.path.exists(dest_filename):
        print("WARNING: {} already exists.".format(dest_filename))
        msg = "Overwrite name? [y|N]"
        try:
            choice = raw_input(msg)
        except NameError:
            # python 3
            choice = input(msg)
        if choice.lower() != 'y':
            print('Abort')
            return 1

    enc_file = open(dest_filename, 'wt')
    enc_file.write(enc)
    enc_file.close()

    # Now show, because often we do this when signing
    # up for a site, so need pw on clipboard
    return show(name)


def pwgen(length):
    """A random password of given length"""

    myrand = random.SystemRandom()
    alphabet = string.ascii_letters + string.digits
    password = ''.join(myrand.choice(alphabet) for _ in range(length))
    return password


def encrypt(contents):
    """Return encrypted 'contents'"""
    return execute(ENCRYPT_CMD, contents)


def decrypt(contents):
    """Return decrypted 'contents'"""
    return execute(DECRYPT_CMD, contents)


def execute(cmd, data_in):
    """Execute 'cmd' on 'stdin' returning 'stdout'"""
    proc = subprocess.Popen(
        cmd.split(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    proc.stdin.write(data_in.encode("utf8"))
    return proc.communicate()[0].decode("utf8")


def show(name, is_visible=False):
    """Display accounts details for name, and put password on clipboard"""

    filename = os.path.join(HOME_PWD, name)
    try:
        if not os.path.exists(filename):
            filename = guess(name)
            basename = os.path.basename(filename)
            print('Guessing {}'.format(bold(basename)))

        enc_file = open(filename, 'rt')
    except IOError:
        print('File not found: {}'.format(filename))
        return 1

    enc = enc_file.read()
    enc_file.close()

    contents = decrypt(enc)
    parts = contents.split('\n')

    password = parts[0]
    username = parts[1]
    print(bold(username))

    if is_visible:
        print(password)
    else:
        copy_to_clipboard(password)

    if len(parts) > 2:
        print('\n'.join(parts[2:]))

    return 0


def guess(name):
    """Guess filename from part of name"""
    res = None
    globs = glob.glob('{}/*{}*'.format(HOME_PWD, name))
    if len(globs) == 1:
        res = globs[0]
        return res
    elif len(globs) > 1:
        print('Did you mean:')
        index = 0
        for option in globs:
            print('{} - {}'.format(index, os.path.basename(option)))
            index += 1
        try:
            try:
                choice = raw_input("Select a choice ? ")
            except NameError:
                # python 3
                choice = input("Select a choice ? ")
            if choice:
                try:
                    choice = int(choice)
                    return globs[choice]
                except ValueError:
                    print("The choice must be an integer")
        except KeyboardInterrupt:
            print('\nKeyboardInterrupt\n')

    raise IOError()


def copy_to_clipboard(msg):
    """Copy given message to clipboard"""
    try:
        proc = subprocess.Popen(CLIP_CMD.split(), stdin=subprocess.PIPE)
        proc.stdin.write(msg.encode("utf8"))
        proc.communicate()
    except OSError as err:
        print('{} -- {}'.format(CLIP_CMD, err))
        print('{} is propably not installed'.format(CLIP_CMD))


def bold(msg):
    """'msg' wrapped in ANSI escape sequence to make it bold"""
    return "\033[1m{msg}\033[0m".format(msg=msg)

if __name__ == '__main__':
    sys.exit(main())
