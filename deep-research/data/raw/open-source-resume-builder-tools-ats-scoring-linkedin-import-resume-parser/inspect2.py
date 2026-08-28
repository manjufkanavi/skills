import json
data = json.load(open('pages.json'))
targets = ['open-resume', 'resume-matcher', 'dev.to', 'github.com/topics', 'edenai', 'resumegenius', 'jobscan', 'enhancv', 'tealhq', 'resumeworded', 'careerflow', 'resumatic', 'resumeup', 'kudoswall', 'open-resume.com']
for i, p in enumerate(data):
    u = p.get('url','')
    if any(t in u for t in targets):
        c = p.get('content','') or ''
        print('='*25, i, u, 'LEN', len(c))
        print(c[:2500])
        print()
