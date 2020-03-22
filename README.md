# Backdoor
A backdoor that is able to run on Windows and Linux.

This is my first project on github so feel free to give tips.

## How to use
#### Client versions
The main version of the client is the Python version but I am currently working on a different one written in Rust
because the Python client is very big if compiled (around 60 MiB). The goal is to implement the same functions on both versions so they are compatible with just one server. THE RUST VERSION IS VERY UNSTABLE AND YOU SHOULD NOT USE IT!

#### Group system
The server uses a group system to control the clients. You can address them with their indices(0, 1, 2, ...) or with the
groups, in which they are. When they connect all clients are automatically in the 'all' group. So for example you can
list all connected clients with `list -s all`. You also can address multiple groups or indices at once for example
`list -s 1 2 3`. If you select one client two times it will be addressed only once: `list -s all 1`.

#### Encryption
The backdoor uses AES encryption in GCM mode with a 256 bit key to encrypt the entire communication.
When using the backdoor its important to change the key. To do so replace the key in server.py (line 204) and in
client.py (line 158) with the output of generate_key.py (both have to be the same).

#### Commands
- `block` - Block a client by IP
- `cam` - Capture camera image
- `close` - Close and remove session
- `down` - Download file from client
- `edit` - Run a text editor and optionally open a file with it
- `exe` - Remote execute terminal command
- `exit` - Exit server and close socket (not closing sessions)
- `group` - Edit sessions groups memberships
- `help` - List available commands or provide detailed help for a specific command
- `history` - View, run, edit, save, or clear previously entered commands
- `list` - List connected sessions
- `logger` - Start/Stop keylogger
- `screen` - Capture screen image
- `set` - Set a settable parameter or show current settings of parameters
- `shell` - Execute a command as if at the OS prompt
- `tag` - Edit sessions tag
- `up` - Upload file to client
- `zip` - Compress to zip archive

## Requirements
- Python 3.6 or higher
- Windows or Linux OS (not tested on mac)

#### Third party modules
- cmd2
- cryptography
- cv2
- mss
- pynput
- texttable

install them with `pip3 install -r requirements.txt`

## TODO
- get clipboard content
- get browser cookies
- DOS attack
- sniff wifi
- kill process
