import argparse
import os
import httpserver


# Usage: httpfs [-v] [-p PORT] [-d PATH-TO-DIR]
parser = argparse.ArgumentParser(description='httpfs is a simple file server.')

parser.add_argument("-v", "--verbose",
                    help="Prints debugging messages.",
                    action='store_true',)
parser.add_argument("-p", "--port", type=int, default=8080,
                    help="Specifies the port number that the server will listen and serve at. Default is 8080.")
parser.add_argument("-d", "--directory", default=os.getcwd(),
                    help="Specifies the directory that the server will use to read/write requested fles. "
                         "Default is the current directory when launching the application.",
                    metavar="PATH-TO-DIR")

args = parser.parse_args()
httpserver.run_server(args.port, args.directory)

