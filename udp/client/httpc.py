import argparse
import httpclient


def output_response(response_headers, response_body, verbose, output_file=None):
    if verbose:
        full_response = response_headers + "\n" + response_body
        if output_file:
            with open(output_file, "w") as f:
                f.writelines(full_response)
        else:
            print(full_response)
    else:
        if output_file:
            with open(output_file, "w") as f:
                f.writelines(response_body)
        else:
            print(response_body)


def run_get(url, router_host, router_port, verbose, headers=None, output_file=None):
    response_headers, response_body = httpclient.http_request("get", url, router_host, router_port, headers)
    output_response(response_headers, response_body, verbose, output_file)


def run_post(url, router_host, router_port, verbose, headers=None, data=None, file=None, output_file=None):
    response_headers, response_body = httpclient.http_request("post", url, router_host, router_port, headers, data, file)
    output_response(response_headers, response_body, verbose, output_file)


# Usage: python httpc.py (get|post) [-v] (-k "k:v")* [-d inline-data] [-f file] URL
parser = argparse.ArgumentParser(description='httpc is a curl-like application but supports HTTP protocol only.')
subparsers = parser.add_subparsers(help='available HTTP requests', dest='command')

# Common args for both subparsers
parent_parser = argparse.ArgumentParser(add_help=False)
parent_parser.add_argument("-rh", "--routerhost",
                           help="Host for router", default="localhost",
                           metavar='router_host')
parent_parser.add_argument("-rp", "--routerport",
                           help="Port for router", default=3000,
                           metavar='router_port')
parent_parser.add_argument("-v", "--verbose",
                           help="Prints the detail of the response such as protocol, status, and headers.",
                           action='store_true',)
parent_parser.add_argument("-k",
                        help="Associates headers to HTTP Request with the format 'key:value'.",
                        metavar='key:value')
parent_parser.add_argument("-o",
                           help="Writes the response to an output file.",
                           metavar='output_file'
                           )
parent_parser.add_argument("URL", help="URL for the request.")

# GET subparser
parser_get = subparsers.add_parser('get',
                                   parents=[parent_parser],
                                   help='get executes a HTTP GET request and prints the response.',
                                   description="Get executes a HTTP GET request for a given URL.")

# POST subparser
parser_post = subparsers.add_parser('post',
                                    parents=[parent_parser],
                                    help='post executes a HTTP POST request and prints the response.',
                                    description="Post executes a HTTP POST request for a given URL with"
                                                " inline data or from file.")
group = parser_post.add_mutually_exclusive_group(required=True)
group.add_argument("-d", help="Associates an inline data to the body HTTP POST request.",
                         metavar='inline-data')
group.add_argument("-f", help="Associates the content of a file to the body HTTP POST request.",
                         metavar='file')

args = parser.parse_args()
router_host = args.routerhost
router_port = args.routerport
verbose = args.verbose
headers = args.k
output_file = args.o
url = args.URL

if headers:
    headers = headers.split(' ')

if args.command == "get":
    run_get(url, router_host, router_port, verbose, headers, output_file)
elif args.command == "post":
    data = args.d
    file = args.f
    run_post(url, router_host, router_port, verbose, headers, data, file, output_file)
