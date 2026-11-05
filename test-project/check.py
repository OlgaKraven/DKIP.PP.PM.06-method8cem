"""HTTP regression collection. Run: py -3 check.py URL cases.json"""
import json,sys,urllib.request,urllib.error
base=sys.argv[1].rstrip('/')
cases=json.load(open(sys.argv[2],encoding='utf-8-sig'))
failed=0
for c in cases:
    try:
        r=urllib.request.urlopen(base+c['path']);status=r.status;data=json.load(r)
    except urllib.error.HTTPError as e:status=e.code;data=json.load(e)
    ok=status==c['status'] and (('ids' not in c) or isinstance(data,list) and [x['id'] for x in data]==c['ids'])
    if 'error' in c:ok=ok and data.get('error')==c['error']
    print(('PASS' if ok else 'FAIL'),c['name'],status,json.dumps(data,ensure_ascii=False));failed+=not ok
print('FAILED',failed,'OF',len(cases));sys.exit(bool(failed))
