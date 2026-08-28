import json
data = json.load(open('pages.json'))
for i, p in enumerate(data):
    u = p.get('url','')
    if 'reactive' in u or 'jsonresume' in u or 'resumake' in u or 'rendercv' in u or 'LapisCV' in u:
        c = p.get('content','') or ''
        print('='*20, i, u, 'LEN', len(c))
        print(c[:1500])
        print()
