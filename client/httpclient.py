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
        redirect_url = re.search('Location: (.*)', response).group(1).strip('\r')
    except AttributeError:
        return None
    return redirect_url


def check_and_handle_redirect(request_type, response, headers, body, input_headers=None, data=None, file=None):
    redirect_url = get_redirect_url(response)
    if not redirect_url:
        return headers, body
    headers, body = http_request(request_type, redirect_url, input_headers, data, file)
    return headers, body


def http_request(request_type, url, headers=None, data=None, file=None):
    if '//' not in url:
        url = '%s%s' % ('//', url)
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = get_host(url)
    path = get_path(url)
    query = get_query(url)
    try:
        conn.connect((host, 80))
        request_string = ""
        if request_type == "get":
            request_string = build_http_get(host, path, query, headers)
        elif request_type == "post":
            request_string = build_http_post(host, path, headers, data, file)
        request = request_string.encode("utf-8")
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
            (headers, body) = check_and_handle_redirect(request_type, response, headers, body, input_headers, data, file)
        return headers, body
    finally:
        conn.close()


def build_http_get(host, path, query=None, headers=None):
    if query:
        request_string = "GET " + path + "?" + query + " HTTP/1.0\r\nHost: " + host + "\r\n"
    else:
        request_string = "GET " + path + " HTTP/1.0\r\nHost: " + host + "\r\n"
    if headers:
        request_string = add_headers(request_string, headers)
    request_string += "\r\n"
    return request_string


def build_http_post(host, path, headers=None, data=None, file=None):
    if file:
        data = read_file_data(file)
    request_string = "POST " + path + " HTTP/1.0\r\nHost: " + host + \
                     "\r\nContent-Length: " + str(len(data)) + "\r\n"
    if headers:
        request_string = add_headers(request_string, headers)
    request_string += "\r\n"
    request_string += data
    return request_string
