#!/usr/bin/env python3
""" kip: Keep Internet Passwords.

kip is a command line tool to storing usernames and passwords
 in gnupg-encrypted text files.

It is intended as an alternative to onepassword, keepass, etc.
Run it for more details.
---

Copyright 2011-2012 Graham King

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
from http.server import BaseHTTPRequestHandler
import ssl
import socketserver
from urllib.parse import parse_qs


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

 If the LAST argument is --serve=my.example.com we start an HTTPS server
 on my.example.com, so you can access your password remotely.

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

    last_arg = argv[len(argv) - 1]
    is_visible = (last_arg == '--print')
    is_serve = last_arg.startswith('--serve')

    if is_serve:
        address = last_arg.split('=')[1]
        http_server(address)

    elif len(argv) == 2 or is_visible:
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

    if isinstance(cmd, str):
        cmd = cmd.split()

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    if data_in:
        proc.stdin.write(data_in.encode("utf8"))

    stdout, stderr = proc.communicate()

    if proc.returncode == 0:
        return stdout.decode("utf8")
    else:
        raise DecryptError(stderr.decode("utf8"))


def show(name, is_visible=False):
    """Display accounts details for name, and put password on clipboard"""

    try:
        enc = load(name)
    except IOError:
        print('File not found for: {} in {}'.format(name, HOME_PWD))
        return 1

    contents = decrypt(enc)

    username, password, notes = split(contents)

    print(bold(username))

    if is_visible:
        print(password)
    else:
        copy_to_clipboard(password)

    if notes:
        print(notes)

    return 0


def load(name, interactive=True):
    """Load contents of an encrypted file, and return those contents.
    Guesses the filename if only a part is given.
    """

    filename = os.path.join(HOME_PWD, name)
    if not os.path.exists(filename):
        filename = guess(name, interactive=interactive)
        basename = os.path.basename(filename)
        print('Guessing {}'.format(bold(basename)))

    enc_file = open(filename, 'rt')

    enc = enc_file.read()
    enc_file.close()

    return enc


def split(contents):
    """Split the contents of a cleartext file and return
    a tuple of (username, password, notes).
    """

    parts = contents.split('\n')

    password = parts[0]
    username = parts[1]

    notes = None
    if len(parts) > 2:
        notes = '\n'.join(parts[2:])

    return username, password, notes


def guess(name, interactive=True):
    """Guess filename from part of name"""
    res = None
    globs = glob.glob('{}/*{}*'.format(HOME_PWD, name))
    if len(globs) == 1:
        res = globs[0]
        return res
    elif len(globs) > 1 and interactive:
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


#
# HTTP server / remote access part
#

def http_server(address):
    """Start an HTTP server to access passwords remotely.
    """

    try:
        gen_cert(address)
    except DecryptError as exc:
        print("Failed to generate SSL certificate. Aborting.")
        print(exc.gpg_msg)
        return 1

    httpd = SockServ((address, 4443), HTTPHandler)
    httpd.socket = ssl.wrap_socket(
            httpd.socket,
            keyfile='key.pem',
            certfile='cacert.pem',
            ssl_version=ssl.PROTOCOL_TLSv1,
            server_side=True)
    httpd.serve_forever()


def gen_cert(address):
    """Generate self-signed private key and SSL certificate.
    Creates files key.pem and cacert.pem in current directory.
    """

    cmd = "openssl req -new -x509 -newkey rsa:2048 -keyout key.pem " + \
          "-out cacert.pem -days 1095 -nodes -subj /C=ZZ/CN={}".format(address)
    execute(cmd, None)


class SockServ(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded TCPServer which sets SO_REUSEADDR on socket"""
    allow_reuse_address = True
    daemon_threads = True


class HTTPHandler(BaseHTTPRequestHandler):
    """Pushes files out over HTTP"""

    HTML = b"""<form method=POST>
                <input type=text name=name placeholder=name />
                <input type=password name=key placeholder=key />
                <input type=submit value=Go />
              </form>"""

    def add_headers(self):
        """Sends generic headers. Does not close headers."""
        self.send_response(200)
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Pragma', 'no-cache')  # HTTP/1.0

    def do_GET(self):                                   # pylint: disable=C0103
        """Serve a GET request"""

        self.add_headers()
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write(self.HTML)

    def do_POST(self):
        length = int(self.headers['content-length'])
        paramstr = self.rfile.read(length).decode('utf8')

        param_dict = parse_qs(paramstr)

        self.add_headers()
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        name = param_dict["name"][0]
        try:
            username, password, notes = self.fetch(name, param_dict['key'][0])
        except IOError:
            err = "File not found for: {}".format(name)
            self.wfile.write(err.encode("utf8"))
            return
        except DecryptError as exc:
            self.wfile.write(b"Decrypt error\n")
            self.wfile.write(exc.gpg_msg.encode("utf8") + b"\n")
            return

        self.wfile.write(username.encode("utf8") + b"\n")
        self.wfile.write(password.encode("utf8") + b"\n")
        if notes:
            self.wfile.write(notes.encode("utf8") + b"\n")

    def fetch(self, name, passphrase):
        """Fetch decrypted contents of file 'name'"""

        enc = load(name, interactive=False)

        decrypt_cmd = ["gpg",
                       "--quiet",
                       "--passphrase",
                       passphrase,
                       "--decrypt"]
        contents = execute(decrypt_cmd, enc)

        try:
            username, password, notes = split(contents)
        except IndexError:
            raise DecryptError(contents)

        return username, password, notes


class DecryptError(Exception):

    def __init__(self, msg):
        super(DecryptError, self).__init__()
        self.gpg_msg = msg


if __name__ == '__main__':
    sys.exit(main())
