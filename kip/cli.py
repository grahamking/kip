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
import argparse
import getpass

VERSION = "0.3.0"

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

Examples:

 $ {name} get ebay.com
 Decrypts {home}ebay.com using gpg
 Copies password (first line) to clipboard
 Echoes ebay username and notes (other lines)

 $ {name} add ebay.com --username graham_king "And some notes"
 Generate random password (pwgen -s1 19)
 Creates file {home}ebay.com with format:
    pw
    username
    notes
 Encrypts and signs it with gpg.

""".format(name=sys.argv[0], home=HOME_PWD + os.path.sep, version=VERSION)

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

    args = parseargs()
    if not args:
        return 1

    # Ensure our home directory exists
    if not os.path.exists(HOME_PWD):
        os.makedirs(HOME_PWD)

    if args.cmd not in CMDS:
        args.filepart = args.cmd
        args.cmd = "get"

    retcode = CMDS[args.cmd](args)

    return retcode


def cmd_get(args):
    """Command to get a password"""
    return show(args.filepart, args.is_print)


def cmd_add(args):
    """Command to create a new entry"""
    if not args.username:
        msg = "Username: "
        try:
            args.username = raw_input(msg)
        except NameError:
            # python 3
            args.username = input(msg)

    pwd = None
    if args.is_prompt:
        pwd = getpass.getpass()

    return create(args.filepart, args.username, args.notes, pwd=pwd)


def cmd_list(args):
    """List stored accounts"""

    glob_filter = args.filepart or "*"
    glob_path = '{}/{}'.format(HOME_PWD, glob_filter)
    print("Listing {}:".format(bold(glob_path)))

    files = []
    for filename in glob.glob(glob_path):
        files.append(os.path.basename(filename))

    files.sort()
    print('\n'.join(files))

    return 0


def cmd_edit(args):
    """Edit an account."""
    name = args.filepart

    try:
        filename = find(name)
        username, password, notes = extract(filename)
    except IOError:
        print('File not found: {}'.format(filename))
        return 1
    print("Editing {}".format(bold(filename)))

    if args.username:
        username = args.username

    if args.is_prompt:
        password = getpass.getpass()

    os.remove(filename)

    create(name, username, notes, pwd=password)

    return 0


def cmd_del(args):
    """Delete an account"""
    name = args.filepart

    try:
        filename = find(name)
    except IOError:
        print('File not found: {}'.format(filename))
        return 1

    msg = "Delete {}? [y|N]".format(bold(filename))
    try:
        choice = raw_input(msg)
    except NameError:
        # python 3
        choice = input(msg)
    if choice.lower() != 'y':
        print('Abort')
        return 1

    os.remove(filename)

    return 1


def parseargs():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
            description="Manage account details in GPG files")

    parser.add_argument("cmd", nargs="?",
            help="Command. One of {}. If not given, defaults to 'get'."\
                    .format(",".join(CMDS.keys())))
    parser.add_argument("filepart", nargs="?",
            help="Filename to display, or part thereof")

    parser.add_argument("--username", "-u",
            help="Username to store. Will prompt if not given.")
    parser.add_argument("--notes", "-n", help="Notes - anything you want")

    parser.add_argument("--prompt", "-p",
            dest="is_prompt",
            action="store_true",
            help="Prompt for password on command line instead of generating it")

    parser.add_argument("--print",
            dest="is_print",
            action="store_true",
            help="Display password instead of copying to clipboard")

    if len(sys.argv) == 1:
        print("{name} v{version}".format(name=sys.argv[0], version=VERSION))
        parser.print_help()
        print(USAGE)
        return None

    args = parser.parse_args()
    return args


def create(name, username, notes=None, **kwargs):
    """Create a new entry"""
    password = kwargs.get("pwd", None)
    if not password:
        # No pw given, make random one
        password = pwgen(LEN_PWD)

    if not notes:
        notes = ''

    file_contents = TEMPLATE.format(
        password=password,
        username=username,
        notes=notes + "\n")
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
    if data_in:
        proc.stdin.write(data_in.encode("utf8"))
    return proc.communicate()[0].decode("utf8")


def show(name, is_visible=False):
    """Display accounts details for name, and put password on clipboard"""

    try:
        filename = find(name)
        username, password, notes = extract(filename)
    except IOError:
        print('File not found: {}'.format(filename))
        return 1

    print(bold(username))

    if is_visible:
        print(password)
    else:
        copy_to_clipboard(password)

    print(notes)

    return 0


def find(name):
    """Find a file matching 'name', prompting for user's help if needed.
    Can raise IOError  - caller must handle it.
    """

    filename = os.path.join(HOME_PWD, name)
    if not os.path.exists(filename):
        filename = guess(name)
        basename = os.path.basename(filename)
        print('Guessing {}'.format(bold(basename)))

    return filename


def extract(filename):
    """Extracts username, password and notes from given file,
    and returns as tuple (username, password, notes).
    """
    enc_file = open(filename, 'rt')     # Can raise IOError - caller must catch

    enc = enc_file.read()
    enc_file.close()

    contents = decrypt(enc)
    parts = contents.split('\n')

    password = parts[0]
    username = parts[1]

    notes = ""
    if len(parts) > 2:
        notes = '\n'.join(parts[2:])

    return (username, password, notes)


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


def cmd_import_from_chrome():
    """Import keys stored in Gnome Keyring by Chrome.

    Depends on gnomekeyring (python lib) which unfortunately is Python2 only,
    so run: python cli.py --import-chrome

    Note that this does NOT import the keys created by export_to_gnome_keyring,
    below. This imports what Chrome stores, the export method below
    pushes kip keys into keyring.
    """
    import gnomekeyring as gk
    import glib

    def clean_domain(domain):
        return domain.replace('http://', '').replace('https://', '').strip('/')

    glib.set_application_name('kip')

    ids = gk.list_item_ids_sync('login')
    for id in ids:

        attrs = gk.item_get_attributes_sync('login', id)
        domain = clean_domain(attrs['signon_realm'])
        username = attrs['username_value']

        info = gk.item_get_info_sync('login', id)
        pwd = info.get_secret()

        msg = "Import %s (%s)? [y|N]" % (domain, username)
        try:
            choice = raw_input(msg)
        except NameError:
            # python 3
            choice = input(msg)

        if choice.lower() != 'y':
            print('Skipping')
            continue

        create(domain, username, pwd=pwd)


def cmd_export_to_gnome_keyring():
    """Write out accounts to Gnome Keyring. Only useful for 'backup',
    if you have keyring tools. There is currently no way to import
    these keys back into kip.

    Requires python2 and gnomekeyring lib.

    Note that this does NOT make the passwords usable to Chrome - this is
    not a counterpart to import_chrome_gnome_keyring.
    """

    import time
    import gnomekeyring as gk
    import glib

    glib.set_application_name('kip')

    keyrings = gk.list_keyring_names_sync()
    if not 'kip' in keyrings:
        gk.create_sync('kip', None)     # None means prompt user for password

    for filename in glob.glob('{}/*'.format(HOME_PWD)):

        user, pwd, notes = extract(filename)
        domain = os.path.basename(filename)

        print("Exporting {} ({})".format(domain, user))
        """
        msg = "Export %s (%s)? [y|N]" % (domain, user)
        try:
            choice = raw_input(msg)
        except NameError:
            # python 3
            choice = input(msg)

        if choice.lower() != 'y':
            print('Skipping')
            continue
        """

        attributes = {
            "username": user.encode("utf8"),
            "notes": notes.encode("utf8"),
            "date_created": str(int(time.time())),
        }

        gk.item_create_sync('kip',
                            gk.ITEM_GENERIC_SECRET,
                            domain,
                            attributes,
                            pwd.encode("utf8"),
                            True)


CMDS = {
    "get": cmd_get,
    "add": cmd_add,
    "list": cmd_list,
    "edit": cmd_edit,
    "del": cmd_del,

    "import_from_chrome": cmd_import_from_chrome,
    "export_to_gnome_keyring": cmd_export_to_gnome_keyring,
}


if __name__ == '__main__':
    sys.exit(main())
