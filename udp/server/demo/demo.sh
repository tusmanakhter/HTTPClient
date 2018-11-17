#!/usr/bin/env bash

# To start server
# python3 httpfs.py -d ./demo

echo "curl output:"
curl -X GET -v localhost:8080/
echo "httpc output:"
python3 ../../client/httpc.py get -v localhost:8080/

echo "curl output:"
curl -X GET -v localhost:8080/test.txt
echo "httpc output:"
python3 ../../client/httpc.py get -v localhost:8080/test.txt

echo "curl output:"
curl -X GET -v localhost:8080/tests.txt
echo "httpc output:"
python3 ../../client/httpc.py get -v localhost:8080/tests.txt

echo "curl output:"
curl -X GET -v localhost:8080/test.exe
echo "httpc output:"
python3 ../../client/httpc.py get -v localhost:8080/test.exe

echo "curl output:"
curl -X GET -v --path-as-is 'localhost:8080/../../'
echo "httpc output:"
python3 ../../client/httpc.py get -v 'localhost:8080/../../'

echo "curl output:"
curl -X POST -v 'localhost:8080/test.py' -d "test"
echo "httpc output:"
python3 ../../client/httpc.py post -v 'localhost:8080/test.py' -d "test"

echo "curl output:"
curl -X POST -v 'localhost:8080/httpfs.py' -d "test"
echo "httpc output:"
python3 ../../client/httpc.py post -v 'localhost:8080/httpfs.py' -d "test"
