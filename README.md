% KIP(1)
% Graham King
% 26 OCT 2012

# NAME

kip - Keeps Internet Passwords. Command line script to keep usernames and passwords in gnupg encrypted text files.

# SYNPOSIS

kip get|add|list|edit|del [filepart] [--username USERNAME] [--notes NOTES] [--prompt] [--print]

# INSTALL

Make sure you have a gnupg key pair:
[GnuPG HOWTO](https://help.ubuntu.com/community/GnuPrivacyGuardHowto).

Latest release: `sudo pip install kip`

Latest dev:

 1. Clone the repo: `git clone https://github.com/grahamking/kip.git`
 1. Install: `sudo python3 setup.py install`

**Ubuntu**: [PPA with 'precise' package](https://launchpad.net/~graham-king/+archive/ppa)

**Arch Linux**: [kip package for Arch](https://aur.archlinux.org/packages.php?ID=62555).
Thanks [Pezz](https://github.com/pezz)!

# COMMANDS

## add

`kip add example.com --usename username`

What it does:

 1. Generates a random password
 2. Writes username and password to text file `~/.kip/passwords/example.com`
 3. Encrypts and signs it by running `gpg --encrypt --sign --armor`
 4. Copies the new password to your clipboard

Add optional notes: `kip add example.com --username username --notes "My notes"`.
You can ask to be pompted for the password, instead of using a random one: `kip add example.com --username username --prompt`

## get

`kip example.com`

What it does:

 1. Looks for `~/.kip/passwords/*example.com*`, decrypts it by running `gpg --decrypt`
 2. Prints your username in bold, and any notes your stored.
 3. Copies your password to the clipboard

## list

`kip list "*.org"`

List contents of your password directory. [filepart] argument is a glob to filter the directory list. You can use ls too!

## edit

`kip edit example.com --username newuser`

Change the username inside a password file.  [filepart] is the file to edit, and --username sets a new username.

## del

`kip del example.com`

Delete a password file. [filepart] is the file to delete. You can use rm too!

## import\_from\_chrome

Import passwords that Chrome stored in Gnome Keyring. This requires gnomekeyring (python lib) and python2.

# DEPENDENCIES

gnupg to encrypt password files, xclip (linux) or pbcopy (OSX) to copy password to clipboard, and python3 but you have that already.

On Ubuntu / Debian: `sudo apt-get install gnupg xclip`

# CONFIGURATION

If you want to use different commands to encrypt / decrypt your files, want longer passwords, etc, you can.  Copy `kip.conf` from the repo to `~/.kip/kip.conf`, and customise it. It's an INI file, using = or : as the delimiter. Make sure the `home` path does not end with a slash.

# NOTES

[GnuPG](http://www.gnupg.org/) is secure, open, multi-platform, and will probably be around forever. Can you say the same thing about the way you store your passwords currently?

I was using the excellent [Keepass](http://en.wikipedia.org/wiki/KeePass) when I got concerned about it no longer being developed or supported. How would I get my passwords out? So I wrote this very simple wrapper for gnupg.

If you live in the command line, I think you will find **kip** makes your life a little bit better.

# FILES

There's 0 magic involved. Your accounts details are in text files, in your home directory. Each one is encrypted with your public key and signed with your private key. You can ditch **kip** at any time.

Browse your files: `ls ~/.kip/passwords/`

Display contents manually: `gpg -d ~/.kip/passwords/facebook`
