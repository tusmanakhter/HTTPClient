#!/usr/bin/env bash

echo "curl output:"
curl -X GET http://httpbin.org/status/418
echo "httpc output:"
python3 httpc.py get http://httpbin.org/status/418

echo "curl output:"
curl -X GET 'http://httpbin.org/get?course=networking&assignment=1'
echo "httpc output:"
python3 httpc.py get 'http://httpbin.org/get?course=networking&assignment=1'

echo "curl output:"
curl -X GET -v 'http://httpbin.org/get?course=networking&assignment=1'
echo "httpc output:"
python3 httpc.py get -v 'http://httpbin.org/get?course=networking&assignment=1'

echo "curl output:\n"
curl -X POST -H Content-Type:application/json -d '{"Assignment": 1}' http://httpbin.org/post
echo "httpc output:"
python3 httpc.py post -k Content-Type:application/json -d '{"Assignment": 1}' http://httpbin.org/post

echo "curl output:"
curl -X POST -d "@README.md" http://httpbin.org/post
echo "httpc output:"
python3 httpc.py post -f "README.md" http://httpbin.org/post

echo "curl output:"
curl -X POST -d "@README.md" -o "curl_output.txt" http://httpbin.org/post
echo "httpc output:"
python3 httpc.py post -f "README.md" -o "httpc_output.txt" http://httpbin.org/post

echo "curl output:"
curl -X GET "google.com"
echo "httpc output:"
python3 httpc.py get -v "google.com"