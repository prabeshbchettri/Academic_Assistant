import json, collections, sys

g = json.load(open('graphify-out/graph.json', encoding='utf-8'))
nodes = {n['id']: n for n in g['nodes']}
SEP = '/'

def top(f):
    if not f:
        return '(none)'
    p = f.replace(chr(92), SEP).split(SEP)
    return p[0] if len(p) > 1 else '(root)'

per = collections.Counter()
kinds = collections.Counter()
for n in g['nodes']:
    per[top(n.get('source_file'))] += 1
    kinds[n.get('kind') or n.get('type') or '?'] += 1
print('NODES PER TOP DIR:', dict(per.most_common()))
print('KINDS:', dict(kinds.most_common(15)))

agg = collections.Counter()
for l in g['links']:
    s = nodes.get(l.get('source'))
    t = nodes.get(l.get('target'))
    if not s or not t:
        continue
    a, b = top(s.get('source_file')), top(t.get('source_file'))
    if a != b and a not in ('(none)', '(root)') and b not in ('(none)', '(root)'):
        agg[(a, b)] += 1
print('\nCROSS-DIR EDGES (dir-level, top 45):')
for (a, b), c in agg.most_common(45):
    print('  %s -> %s: %d' % (a, b, c))

rt = collections.Counter(l.get('relation') for l in g['links'])
print('\nRELATIONS:', dict(rt.most_common(20)))
conf = collections.Counter(l.get('confidence') for l in g['links'])
print('CONFIDENCE:', dict(conf.most_common(8)))

files = collections.Counter(n.get('source_file') for n in g['nodes'] if n.get('source_file'))
print('\nFILES IN GRAPH (%d):' % len(files))
for f, c in sorted(files.items()):
    print('  %-70s %d' % (f, c))
