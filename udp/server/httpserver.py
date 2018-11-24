import sys
sys.path.insert(0, '../')
import socket
import os
import mimetypes
import random
from packet import Packet
from datetime import datetime

seq_number = -1
client_seq_number = -1


class SynError(Exception):
    pass


syn_error = SynError()


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
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        conn.bind(('', port))
        print('Server listening on port', port)
        handle_client(conn, directory)
    finally:
        print("false")
        conn.close()


def send_syn_ack(conn, recv_packet, sender):
    global seq_number
    seq_number = random.randint(1, 2147483647)
    packet = Packet(packet_type=Packet.SYN_ACK,
                    seq_num=seq_number,
                    peer_ip_addr=recv_packet.peer_ip_addr,
                    peer_port=recv_packet.peer_port,
                    payload=str(recv_packet.seq_num + 1).encode("utf-8"))
    conn.sendto(packet.to_bytes(), sender)


def send_data(conn, response, recv_packet, sender):
    global seq_number
    packet = Packet(packet_type=Packet.DATA,
                    seq_num=seq_number,
                    peer_ip_addr=recv_packet.peer_ip_addr,
                    peer_port=recv_packet.peer_port,
                    payload=response)
    conn.sendto(packet.to_bytes(), sender)


def check_ack_seq(received_seq):
    global seq_number
    print("ack: " + str(seq_number+1) + "///" + str(received_seq))
    if received_seq == seq_number + 1:
        return True
    else:
        return False


def check_client_seq(received_seq):
    global client_seq_number
    print("client: " + str(client_seq_number) + "///" + str(received_seq))
    if received_seq == client_seq_number:
        return True
    else:
        return False


def build_response(recv_packet, directory):
    request = b''
    request += recv_packet.payload
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
    return response_string


def handle_client(conn, directory):
    global seq_number
    global client_seq_number
    while True:
        data, sender = conn.recvfrom(1024)
        print('New client from', str(sender[0]) + ":" + str(sender[1]))

        # Receive SYN
        recv_packet = Packet.from_bytes(data)

        if recv_packet.packet_type == Packet.SYN:
            print("Received SYN")
            client_seq_number = recv_packet.seq_num
            # Send SYN-ACK
            print("Sending SYN_ACK")
            send_syn_ack(conn, recv_packet, sender)
        else:
            continue

        packet_type = -1
        correct_seq = False

        try:
            while packet_type != Packet.ACK or not correct_seq:
                # Receive ACK
                response, sender = conn.recvfrom(1024)
                recv_packet = Packet.from_bytes(response)
                packet_type = recv_packet.packet_type
                correct_seq = check_ack_seq(recv_packet.seq_num)
                if packet_type == Packet.SYN:
                    raise syn_error
        except SynError:
            continue

        print("Received ACK\n3-Way Handshake Finished")
        packet_type = Packet.DATA
        correct_seq = False
        client_seq_number += 1
        seq_number += 1

        try:
            while packet_type == Packet.DATA or not correct_seq:
                response, sender = conn.recvfrom(1024)
                recv_packet = Packet.from_bytes(response)
                print("Router: ", sender)
                print("Packet: ", recv_packet)
                print("Payload: ", recv_packet.payload.decode("utf-8"))
                correct_seq = check_client_seq(recv_packet.seq_num)
                packet_type = recv_packet.packet_type
                if packet_type == Packet.SYN:
                    raise syn_error
                response_string = build_response(recv_packet, directory)
                send_data(conn, response_string, recv_packet, sender)
        except SynError:
            continue


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
