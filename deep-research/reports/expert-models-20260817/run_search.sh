#!/bin/bash
API_KEY="sk-tinyfish-vHbgNi2R-tVLAXFixslJ3lk5iz71dIsE"
mkdir -p results
i=0
while IFS= read -r q; do
  i=$((i+1))
  enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$q")
  out="results/query_$(printf '%02d' $i).json"
  curl -s "https://api.search.tinyfish.ai?query=${enc}" -H "X-API-Key: ${API_KEY}" -o "$out"
  sleep 0.3
done < queries.txt
echo "done $i queries"
