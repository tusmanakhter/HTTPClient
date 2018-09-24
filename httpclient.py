import socket
from urllib.parse import urlparse


def get_host(url):
    return urlparse(url).netloc


def get_path(url):
    return urlparse(url).path


def get_query(url):
    return urlparse(url).query


def add_headers(request, headers):
    for header in headers:
        key, value = header.split(":")
        request += key + ": " + value + "\r\n"
    return request


def read_file_data(file):
    file_data = ""
    with open(file) as f:
        lines = f.read().splitlines()
        for line in lines:
            file_data += line
    return file_data


def http_get(url, headers=None):
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = get_host(url)
    path = get_path(url)
    query = get_query(url)
    try:
        conn.connect((host, 80))
        line = "GET " + path + "?" + query + " HTTP/1.0\r\nHost: " + host + "\r\n"
        if headers:
            line = add_headers(line, headers)
        line += "\r\n"
        request = line.encode("utf-8")
        conn.sendall(request)
        response = b''
        while True:
            packet = conn.recv(len(request))
            if not packet:
                break
            response += packet
        (headers, body) = response.decode("utf-8").split("\r\n\r\n")
        return headers, body
    finally:
        conn.close()


def http_post(url, headers=None, data=None, file=None):
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = get_host(url)
    path = get_path(url)
    try:
        conn.connect((host, 80))
        if file:
            data = read_file_data(file)
        line = "POST " + path + " HTTP/1.0\r\nHost: " + host + \
               "\r\nContent-Length: " + str(len(data)) + "\r\n"
        if headers:
            line = add_headers(line, headers)
        line += "\r\n"
        line += data
        request = line.encode("utf-8")
        conn.sendall(request)
        response = b''
        while True:
            packet = conn.recv(len(request))
            if not packet:
                break
            response += packet
        (headers, body) = response.decode("utf-8").split("\r\n\r\n")
        return headers, body
    finally:
        conn.close()
