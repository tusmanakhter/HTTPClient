import socket
import re
from urllib.parse import urlparse


def get_host(url):
    return urlparse(url).netloc


def get_path(url):
    path = urlparse(url).path
    if not path:
        path = "/"
    return path


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


def get_status_code(response):
    status_code_match = re.match('.*HTTP/[0-9]\.[0-9] ([0-9]{3}) (.*)', response)
    status_code = status_code_match.group(1)
    status_code_message = status_code_match.group(2)
    return status_code, status_code_message


def get_redirect_url(response):
    try:
        redirect_url = re.search('Location: (.*)', response).group(1)
    except AttributeError:
        return None
    return redirect_url


def check_and_handle_redirect(request_type, response, headers, body, input_headers=None, data=None, file=None):
    redirect_url = get_redirect_url(response)
    if not redirect_url:
        return headers, body
    if request_type == "get":
        headers, body = http_get(redirect_url, input_headers)
    elif request_type == "post":
        headers, body = http_post(redirect_url, input_headers, data, file)
    return headers, body


def http_get(url, headers=None):
    if '//' not in url:
        url = '%s%s' % ('//', url)
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = get_host(url)
    path = get_path(url)
    query = get_query(url)
    try:
        conn.connect((host, 80))
        if query:
            line = "GET " + path + "?" + query + " HTTP/1.0\r\nHost: " + host + "\r\n"
        else:
            line = "GET " + path + " HTTP/1.0\r\nHost: " + host + "\r\n"
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
        try:
            response = response.decode("utf-8")
        except UnicodeDecodeError:
            response = response.decode("iso-8859-1")
        input_headers = headers
        (headers, body) = response.split("\r\n\r\n")
        status_code, status_code_message = get_status_code(response)
        if 300 <= int(status_code) <= 304:
            (headers, body) = check_and_handle_redirect("get", response, headers, body, input_headers)
        return headers, body
    finally:
        conn.close()


def http_post(url, headers=None, data=None, file=None):
    if '//' not in url:
        url = '%s%s' % ('//', url)
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
        try:
            response = response.decode("utf-8")
        except UnicodeDecodeError:
            response = response.decode("iso-8859-1")
        input_headers = headers
        (headers, body) = response.split("\r\n\r\n")
        status_code, status_code_message = get_status_code(response)
        if 300 <= int(status_code) <= 304:
            (headers, body) = check_and_handle_redirect("post", response, headers, body, input_headers, data, file)
        return headers, body
    finally:
        conn.close()
