import json
data = json.load(open('pages.json'))
print("TOTAL", len(data))
for i, p in enumerate(data):
    print(i, p.get('url',''))
