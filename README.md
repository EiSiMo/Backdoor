# Backdoor
A backdoor that is able to run on Windows and Linux.

## How to install
First you should have [downloaded](https://www.python.org/downloads/ "Python.org") and installed Python 3.7 or a later version.

Download the repository

    git clone https://github.com/EiSiMo/Backdoor
    
Navigate to the folder

    cd Backdoor/client_python
    
or

    cd Backdoor/server_python
    
Install the requirements

    pip3 install -r requirements.txt

If you want to know how to compile the client to a binary file check out [pyinstaller](https://www.pyinstaller.org/ "Pyinstaller.org").
Tip: maybe the -w (no popup window) -F (all in one file) flags are interesting for you.

## How to use
#### Client versions
The main version of the client is the Python version but I am currently working on a different one written in Rust
because the Python client is very big if compiled (around 60 MiB). The goal is to implement the same functions on both
 versions so they are compatible with just one server. THE RUST VERSION IS VERY UNSTABLE AND YOU SHOULD NOT USE IT!

#### Group system
The server uses a group system to control the clients. You can address them with their indices(0, 1, 2, ...) or with the
groups, in which they are. When they connect, all clients are automatically in the 'all' group. So for example you can
list all connected clients with `list -s all`. You also can address multiple groups or indices at once for example
`list -s 1 2 3`. If you select one client two times it will be addressed only once: `list -s all 1`.

#### Encryption
The backdoor uses 2048 bit RSA to exchange the AES key which the server generates. Every sessions has its own AES key.
AES is used in the 256 bit GCM mode.

#### Commands
| Command   | Description                                                                    |
| --------- | ------------------------------------------------------------------------------ |
| `block`   | Block a client by IP address                                                   |
| `cam`     | Capture camera image                                                           |
| `clip`    | Get/Set clipboard content                                                      |
| `close`   | Close and remove session                                                       |
| `crypt`   | En/Decrypt a file or all files in a directory with a password                  |
| `down`    | Download file from client                                                      |
| `edit`    | Run a text editor and optionally open a file with it                           |
| `exe`     | Remote execute terminal command                                                |
| `exit`    | Exit server and close socket (not closing sessions)                            |
| `group`   | Edit sessions groups memberships                                               |
| `help`    | List available commands or provide detailed help for a specific command        |
| `history` | View, run, edit, save, or clear previously entered commands                    |
| `list`    | List connected sessions                                                        |
| `logger`  | Start/Stop keylogger                                                           |
| `screen`  | Capture screen image                                                           |
| `set`     | Set a settable parameter or show current settings of parameters                |
| `shell`   | Execute a command as if at the OS prompt                                       |
| `tag`     | Edit sessions tag                                                              |
| `up`      | Upload file to client                                                          |
| `zip`     | Compress to zip archive                                                        |

## TODO
- Extract browser cookies
- Perform a DOS attack
- Sniff wifi
- Mine crypto currency
- Search and use printers in the network
