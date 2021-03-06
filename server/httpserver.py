import socket
import threading
import os
import mimetypes
from datetime import datetime


def create_headers(response_code, content_type=None, content_disposition=None):
    header = ''
    if response_code == 200:
        header += 'HTTP/1.0 200 OK\r\n'
    elif response_code == 404:
        header += 'HTTP/1.0 404 Not Found\r\n'
    elif response_code == 403:
        header += 'HTTP/1.0 403 Forbidden\r\n'
    header += 'Connection: close\r\n'
    header += 'Server: httpfs server\r\n'
    date = datetime.utcnow()
    header += "Date: " + date.strftime("%a, %d %b %Y %H:%M:%S GMT\r\n")
    if content_type:
        header += "Content-type: " + content_type + "\r\n"
    if content_disposition:
        header += "Content-disposition: " + content_disposition
    header += "\r\n"
    return header


def get_content_type(path):
    mimetypes.init()
    extensions = mimetypes.types_map.copy()
    extensions.update({
        '': 'text/plain',  # Default
        '.py': 'text/plain',  # Python files type such as this one
    })
    base, ext = os.path.splitext(path)
    if ext in extensions:
        return extensions[ext]
    else:
        ext = ext.lower()  # Try with lowercase
        if ext in extensions:
            return extensions[ext]
        else:
            return extensions['']  # Set default


def get_content_disposition(path):
    mimetypes.init()
    extensions = mimetypes.types_map.copy()
    extensions.update({
        '': 'text/plain',  # Default
        '.py': 'text/plain',  # Python files type such as this one
    })
    base, ext = os.path.splitext(path)
    if ext in extensions:
        file_type = extensions[ext]
    else:
        ext = ext.lower()  # Try with lowercase
        if ext in extensions:
            file_type = extensions[ext]
        else:
            file_type = extensions['']  # Set default
    file_type = file_type.split('/')[0]
    if file_type in ['video', 'audio', 'application', 'image']:
        return "attachment"
    else:
        return None


def split_request(line):
    line_array = line.split()
    request_type = line_array[0]
    path = line_array[1].split("?")[0]  # Ignore query parameters
    protocol = line_array[2]
    return request_type, path, protocol


def run_server(port, directory):
    host = ""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        listener.bind((host, port))
        listener.listen(1)
        print('Server listening on port', port)
        while True:
            conn, addr = listener.accept()
            threading.Thread(target=handle_client, args=(conn, addr, directory)).start()
    finally:
        listener.close()


def handle_client(conn, addr, directory):
    print('New client from', addr)
    try:
        request = b''
        packet = conn.recv(1024)
        request += packet
        request = request.decode().split('\r\n\r\n')
        headers = request[0]
        body = request[1]
        header_lines = headers.split('\r\n')
        request_line = header_lines[0]
        request_type, path, protocol = split_request(request_line)
        if request_type == "GET":
            response_string = build_http_get(path, directory)
        elif request_type == "POST":
            response_string = build_http_post(path, directory, body)
        conn.sendall(response_string)
    finally:
        conn.close()


def build_http_get(path, directory):
    response_data = ''
    if path == "/":
        files = os.listdir(directory)
        for file in files:
            response_data += file + "\n"
        response_header = create_headers(200)
    elif "../" in path:
        response_header = create_headers(403)
        response_data = 'You do not have access to other directories\r\n'
    else:
        try:
            file = open(directory + path, 'r')
            response_data = file.read() + "\r\n"
            file.close()
            content_type = get_content_type(path)
            content_disposition = get_content_disposition(path)
            response_header = create_headers(200, content_type, content_disposition)
        except FileNotFoundError:
            response_header = create_headers(404)
            response_data = 'This file does not exist\r\n'
    response = (response_header + response_data).encode()
    return response


def build_http_post(path, directory, data):
    if path == "/httpfs.py" or path == "/httpserver.py":
        response_header = create_headers(403)
        response_data = 'You do not have access to modify this file\r\n'
    elif "../" in path:
        response_header = create_headers(403)
        response_data = 'You do not have access to other directories\r\n'
    else:
        try:
            open(directory + path, 'r')
            response_data = "File overwritten.\r\n"
        except FileNotFoundError:
            response_data = "File created.\r\n"
        finally:
            try:
                file = open(directory + path, 'w')
                file.write(data)
                file.close()
                response_header = create_headers(200)
            except FileNotFoundError:
                response_header = create_headers(404)
                response_data = "This directory does not exist on the server.\r\n"
    response = (response_header + response_data).encode()
    return response
