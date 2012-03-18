
kip Keeps Internet Passwords.

**Command line script to keep usernames and passwords in gnupg encrypted text files**

## Install

Make sure you have a gnupg key pair: [GnuPG HOWTO](https://help.ubuntu.com/community/GnuPrivacyGuardHowto).

Latest release:

    sudo pip install kip

Latest dev:

 1. Clone the repo: `git clone https://github.com/grahamking/kip.git`
 1. Install: `sudo python setup.py install`

## Store

    kip example.com username

What it does:

 1. Generates a random password
 2. Writes username and password to text file `~/.kip/passwords/example.com`
 3. Encrypts and signs it by running `gpg --encrypt --sign --armor`
 4. Copies the new password to your clipboard

Add optional notes: `kip example.com username "My notes"`.
You can also pipe in your password of choice: `echo S3cret | kip example.com username`

## Retrieve

    kip example.com

What it does:

 1. Looks for `~/.kip/passwords/*example.com*`, decrypts it by running `gpg --decrypt`
 2. Prints your username in bold, and any notes your stored.
 3. Copies your password to the clipboard

## Misc

### Dependencies


  - gnupg: to encrypt password files
  - xclip (linux) or pbcopy (OSX): to copy password to clipboard
  - (and python, but you have that already)

On Ubuntu / Debian: `sudo apt-get install gnupg xclip`

### Configuration

If you want to use different commands to encrypt / decrypt your files, want longer passwords, etc, you can.  Copy `kip.conf` from the repo to `~/.kip/kip.conf`, and customise it. It's an INI file, using = or : as the delimiter. Make sure the `home` path does not end with a slash.

### Motivation

[GnuPG](http://www.gnupg.org/) is secure, open, multi-platform, and will probably be around forever. Can you say the same thing about the way you store your passwords currently?

I was using the excellent [Keepass](http://en.wikipedia.org/wiki/KeePass) when I got concerned about it no longer being developed or supported. How would I get my passwords out? So I wrote this very simple wrapper for gnupg.

If you live in the command line, I think you will find **kip** makes your life a little bit better.

### Manual override

There's 0 magic involved. Your accounts details are in text files, in your home directory. Each one is encrypted with your public key and signed with your private key. You can ditch **kip** at any time.

Browse your files: `ls ~/.kip/passwords/`

Display contents manually: `gpg -d ~/.kip/passwords/facebook`
