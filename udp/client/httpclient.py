import sys
sys.path.insert(0, '../')
import socket
import re
import ipaddress
import random
from urllib.parse import urlparse
from packet import Packet


def get_host(url):
    return urlparse(url).hostname


def get_port(url):
    port = urlparse(url).port
    if not port:
        return 80
    return int(port)


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


def send_syn(conn, router_host, router_port, ip, port):
    print("3-Way Handshake Started\nSending SYN")
    seq_number = random.randint(1, 2147483647)
    packet = Packet(packet_type=Packet.SYN,
                    seq_num=seq_number,
                    peer_ip_addr=ip,
                    peer_port=port,
                    payload='')
    conn.sendto(packet.to_bytes(), (router_host, router_port))
    return seq_number


def send_ack(conn, recv_packet, router_host, router_port):
    packet = Packet(packet_type=Packet.ACK,
                    seq_num=recv_packet.seq_num + 1,
                    peer_ip_addr=recv_packet.peer_ip_addr,
                    peer_port=recv_packet.peer_port,
                    payload='')
    conn.sendto(packet.to_bytes(), (router_host, router_port))


def send_data(conn, request, router_host, router_port, ip, port):
    packet = Packet(packet_type=Packet.DATA,
                    seq_num=1,
                    peer_ip_addr=ip,
                    peer_port=port,
                    payload=request)
    conn.sendto(packet.to_bytes(), (router_host, router_port))
    print('Send "{}" to router'.format(request))


def check_piggyback_seq(seq_number, recv_packet):
    received_seq = int(recv_packet.payload.decode("utf-8"))
    if received_seq == seq_number:
        return True
    else:
        return False


def http_request(request_type, url, router_host, router_port, headers=None, data=None, file=None):
    if '//' not in url:
        url = '%s%s' % ('//', url)
    timeout = 5
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.settimeout(timeout)
    host = get_host(url)
    port = get_port(url)
    path = get_path(url)
    query = get_query(url)
    ip = ipaddress.ip_address(socket.gethostbyname(host))

    packet_type = -1
    correct_seq = True
    while packet_type != Packet.SYN_ACK or not correct_seq:
        # Send SYN
        seq_number = send_syn(conn, router_host, router_port, ip, port)
        try:
            # Receive SYN-ACK
            print("Waiting for SYN-ACK")
            response, sender = conn.recvfrom(1024)
            recv_packet = Packet.from_bytes(response)
            packet_type = recv_packet.packet_type
            correct_seq = check_piggyback_seq(seq_number + 1, recv_packet)
        except socket.timeout:
            pass

    print("Received SYN-ACK")
    # Send ACK
    print("Sending ACK")
    send_ack(conn, recv_packet, router_host, router_port)

    try:
        request_string = ""
        if request_type == "get":
            request_string = build_http_get(host, path, query, headers)
        elif request_type == "post":
            request_string = build_http_post(host, path, headers, data, file)
        request = request_string.encode("utf-8")

        # Send the data
        send_data(conn, request, router_host, router_port, ip, port)

        # Try to receive a response within timeout
        print('Waiting for a response')
        response, sender = conn.recvfrom(1024)
        packet = Packet.from_bytes(response)
        print('Router: ', sender)
        print('Packet: ', packet)
        try:
            response = packet.payload.decode("utf-8")
            print('Payload: ' + response)
        except UnicodeDecodeError:
            response = packet.payload.decode("iso-8859-1")
            print('Payload: ' + response)
        input_headers = headers
        try:
            (headers, body) = response.split("\r\n\r\n")
        except ValueError:
            headers = response.split("\r\n\r\n")[0]
            body = ""
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
