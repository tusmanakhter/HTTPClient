import sys
sys.path.insert(0, '../')
import socket
import re
import ipaddress
import random
from urllib.parse import urlparse
from packet import Packet

seq_number = -1
server_seq_number = -1


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


def send_syn(conn, router_host, router_port, ip, port):
    global seq_number
    print("3-Way Connection Handshake Started\nSending SYN")
    seq_number = random.randint(1, 2147483647)
    packet = Packet(packet_type=Packet.SYN,
                    seq_num=seq_number,
                    peer_ip_addr=ip,
                    peer_port=port,
                    payload='')
    conn.sendto(packet.to_bytes(), (router_host, router_port))


def send_ack(conn, recv_packet, router_host, router_port):
    global server_seq_number
    packet = Packet(packet_type=Packet.ACK,
                    seq_num=server_seq_number,
                    peer_ip_addr=recv_packet.peer_ip_addr,
                    peer_port=recv_packet.peer_port,
                    payload='')
    conn.sendto(packet.to_bytes(), (router_host, router_port))


def send_fin(conn, recv_packet, router_host, router_port):
    global seq_number
    packet = Packet(packet_type=Packet.DATA,
                    seq_num=seq_number,
                    peer_ip_addr=recv_packet.peer_ip_addr,
                    peer_port=recv_packet.peer_port,
                    payload='FIN'.encode("utf-8"))
    conn.sendto(packet.to_bytes(), (router_host, router_port))


def send_data(conn, recv_packet, request, router_host, router_port):
    global seq_number
    packet = Packet(packet_type=Packet.DATA,
                    seq_num=seq_number,
                    peer_ip_addr=recv_packet.peer_ip_addr,
                    peer_port=recv_packet.peer_port,
                    payload=request)
    conn.sendto(packet.to_bytes(), (router_host, router_port))


def check_piggyback_seq(recv_packet):
    global seq_number
    received_seq = int(recv_packet.payload.decode("utf-8"))
    if received_seq == seq_number + 1:
        return True
    else:
        return False


def check_ack_seq(received_seq):
    global seq_number
    if received_seq == seq_number + 1:
        return True
    else:
        return False


def check_server_seq(received_seq):
    global server_seq_number
    if received_seq == server_seq_number:
        return True
    else:
        return False


def increase_frame():
    global seq_number
    seq_number += 1


def increase_expected_frame():
    global server_seq_number
    server_seq_number += 1


def http_request(request_type, url, router_host, router_port, headers=None, data=None, file=None):
    global seq_number
    global server_seq_number
    if '//' not in url:
        url = '%s%s' % ('//', url)
    timeout = 1
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.settimeout(timeout)
    host = get_host(url)
    port = get_port(url)
    path = get_path(url)
    query = get_query(url)
    ip = ipaddress.ip_address(socket.gethostbyname(host))

    packet_type = -1
    correct_seq = False

    # Send SYN
    send_syn(conn, router_host, router_port, ip, port)

    while packet_type != Packet.SYN_ACK or not correct_seq:
        try:
            # Receive SYN-ACK
            print("Waiting for SYN-ACK")
            response, sender = conn.recvfrom(1024)
            recv_packet = Packet.from_bytes(response)
            packet_type = recv_packet.packet_type
            correct_seq = check_piggyback_seq(recv_packet)
        except socket.timeout:
            # Send SYN
            send_syn(conn, router_host, router_port, ip, port)

    server_seq_number = recv_packet.seq_num
    increase_expected_frame()
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
        increase_frame()
        send_data(conn, recv_packet, request, router_host, router_port)

        packet_type = -1
        correct_seq = False

        # Try to receive a response within timeout
        while packet_type != Packet.DATA or not correct_seq:
            try:
                print('Waiting for a response')
                response, sender = conn.recvfrom(1024)
                recv_packet = Packet.from_bytes(response)
                packet_type = recv_packet.packet_type
                correct_seq = check_server_seq(recv_packet.seq_num)
                response = recv_packet.payload.decode("utf-8")
                try:
                    (headers, body) = response.split("\r\n\r\n")
                except ValueError:
                    headers = response.split("\r\n\r\n")[0]
                    body = ""
            except socket.timeout:
                send_ack(conn, recv_packet, router_host, router_port)
                send_data(conn, recv_packet, request, router_host, router_port)
        print('Received response, 3-Way Termination Handshake Started')
        increase_frame()
        while True:
            print('Waiting for FIN ACK')
            try:
                send_fin(conn, recv_packet, router_host, router_port)
                response, sender = conn.recvfrom(1024)
                recv_packet = Packet.from_bytes(response)
                packet_type = recv_packet.packet_type
                if packet_type == Packet.ACK:
                    correct_seq = check_ack_seq(recv_packet.seq_num)
                    if correct_seq:
                        break
            except socket.timeout:
                continue
        print('Received FIN ACK')
        received_fin = False
        increase_expected_frame()
        increase_expected_frame()
        conn.settimeout(10)
        while True:
            print('Waiting for FIN')
            try:
                response, sender = conn.recvfrom(1024)
                recv_packet = Packet.from_bytes(response)
                packet_type = recv_packet.packet_type
                correct_seq = check_server_seq(recv_packet.seq_num+1)
                if packet_type == Packet.DATA and correct_seq:
                    if recv_packet.payload.decode("utf-8") == 'FIN':
                        print('Received FIN, sending ACK')
                        received_fin = True
                        send_ack(conn, recv_packet, router_host, router_port)
            except socket.timeout:
                if received_fin:
                    break
                continue
        print('Waiting enough time to close connection, here is the data ...\n')
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
