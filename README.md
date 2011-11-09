
## Usage

**Install**: Just copy kip onto your path: `cp kip.py ~/bin/kip`

Make sure you have a gnupg key pair: [GnuPG HOWTO](https://help.ubuntu.com/community/GnuPrivacyGuardHowto).

**Store a new password**: `kip example.com username "Notes"`
What it does:
  1. Generates a random password
  2. Writes username and password to text file `~/.kip/example.com`
  3. Encrypts and signs it by running `gpg --encrypt --sign --armor`
  4. Copies the new password to your X-windows clipboard

Notes are optional.
You can also pipe in your password of choice: `echo S3cret | kip example.com username`

**Retrieve a password**: `kip example.com`
What it does:
 1. Looks for `~/.kip/*example.com*`
 2. Prints your username in bold, and any notes your stored.
 3. Copies your password to the X-windows clipboard

## Dependencies


  - gnupg: to encrypt password files
  - xclip: to copy password to X clipboard
  - (and python, but you have that already)

On Ubuntu / Debian: `sudo apt-get install gnupg xclip`

## Motivation

[GnuPG](http://www.gnupg.org/) is secure, open, multi-platform, and will probably be around forever. Can you say the same thing about the way you store your passwords currently?

I was using the excellent [Keepass](http://en.wikipedia.org/wiki/KeePass) when I got concerned about it no longer being developed or supported. How would I get my passwords out. So I wrote this very simple wrapper for gnupg.

If you live in the command line, I think you will find **kip** makes your life a little bit better.

