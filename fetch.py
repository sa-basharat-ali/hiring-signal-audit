"""Snapshot public job boards (Ashby, Greenhouse, Lever) -> data/snapshot.json.

usage: python3 fetch.py    (needs network, about a minute)

Two company lists:
  known   - boards I maintain by hand for my own job search (slug + ATS checked by opening the board)
  funded  - companies named in funding news Oct 2026 (my funding scout), resolved by guessing slugs
Every slug is probed on all three ATSs, so a hit on the "wrong" ATS is visible too.
"""
import csv, json, os, re, sys, unicodedata, urllib.request, urllib.parse, datetime as dt
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'data', 'snapshot.json')
UA = {'User-Agent': 'Mozilla/5.0 (hiring-signal-audit; basharat.net)', 'Accept': 'application/json'}
TEXT = 1500  # description chars kept per posting, enough to read "About <company>"

KNOWN = {  # slug -> ats, from outreach/scout.py and lead-scout-state.json (Oct 14 2026)
    **{s: 'ashby' for s in (
        'openai cohere sardine socure upside perplexity jerry.ai crosby headway january legora confido permitflow angi '
        'notion traba vanta rain sentilink profound harvey payabli trm-labs strava g2 madhive decagon claylabs modal linear '
        'mercor deel ironcladhq alchemy nerdwallet candidhealth revenuecat gamechanger talkiatry bestow clair persona numeric '
        'orb cube anomalo datafold orum junior melotech pave sierra elevenlabs lovable runpod rillet simile monaco '
        'moderntreasury footprint mesh corgi cedar ambrook whop taxwire zip vercel posthog replit cursor baseten fireworks '
        'writer hightouch airbyte motherduck 1password arq alternativepayments bevel citizen crusoe gptzero hang aaru '
        'advanced-systems-group airops april assorthealth atlan beaconsoftware braintrust brightwheel burklandassociates '
        'clubhouse column counsel cyberhaven cygnify datawizz dearestcare dualentry eliseai embedding-vc emergence encord '
        'endex exa factory farsight firststreet fluidstack gradient-labs grow-therapy halluminate handshake harmonic haus '
        'hazel healthleap hyperbolic infisical junction kaizenlabs kit lightfield listenlabs mem0 mirage miter nominal '
        'northslope-technologies openevidence outtake owner partiful pearlhealth plaid readme rogo safelease satispay '
        'sentient serval socket speak squadhealth stainlessapi stedi stepful stuut-ai substack suno tem tennr titan-msp '
        'truelogic turbopuffer twenty vapi versemedical wealthsimple workos zoomlogi').split()},
    'metronome': 'greenhouse', 'highnote': 'greenhouse', 'flowcode': 'greenhouse', 'trove': 'greenhouse',
    'basis': 'lever', 'finix': 'lever', 'grand': 'lever',
}


def get(u):
    for _ in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25))
        except urllib.error.HTTPError as e:
            if e.code in (404, 400, 410):
                return None
        except Exception:
            pass
    return 'error'


def strip(h):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', urllib.parse.unquote(h or ''))).strip()


def ashby(slug):
    d = get('https://api.ashbyhq.com/posting-api/job-board/' + urllib.parse.quote(slug))
    if not isinstance(d, dict):
        return d
    return {'name': None, 'jobs': [{
        'id': j['id'], 'title': j.get('title', ''), 'team': j.get('team') or j.get('department') or '',
        'location': j.get('location') or '', 'secondary': [x.get('location') for x in j.get('secondaryLocations') or []],
        'remote': j.get('isRemote'), 'published': j.get('publishedAt'), 'updated': None,
        'text': (j.get('descriptionPlain') or strip(j.get('descriptionHtml')))[:TEXT]} for j in d.get('jobs', [])]}


def greenhouse(slug):
    meta = get(f'https://boards-api.greenhouse.io/v1/boards/{slug}')
    if not isinstance(meta, dict):
        return meta
    d = get(f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true')
    if not isinstance(d, dict):
        return d
    return {'name': meta.get('name'), 'jobs': [{
        'id': str(j['id']), 'title': j.get('title', ''),
        'team': ', '.join(x.get('name', '') for x in j.get('departments') or []),
        'location': (j.get('location') or {}).get('name', ''), 'secondary': [], 'remote': None,
        'published': j.get('first_published'), 'updated': j.get('updated_at'),
        'text': strip(__import__('html').unescape(j.get('content') or ''))[:TEXT]} for j in d.get('jobs', [])]}


def lever(slug):
    d = get(f'https://api.lever.co/v0/postings/{slug}?mode=json')
    if not isinstance(d, list):
        return d
    out = []
    for j in d:
        c = j.get('categories') or {}
        out.append({'id': j['id'], 'title': j.get('text', ''), 'team': c.get('team') or c.get('department') or '',
                    'location': c.get('location') or '', 'secondary': c.get('allLocations') or [],
                    'remote': j.get('workplaceType') == 'remote',
                    'published': dt.datetime.fromtimestamp(j['createdAt'] / 1000, dt.timezone.utc).isoformat()
                    if j.get('createdAt') else None, 'updated': None,
                    'text': (j.get('descriptionPlain') or strip(j.get('description')))[:TEXT]})
    return {'name': None, 'jobs': out}


ATS = {'ashby': ashby, 'greenhouse': greenhouse, 'lever': lever}


def slug_guesses(name):
    """What a naive resolver tries: the name squashed, hyphenated, and its first word."""
    n = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r'\b(inc|labs?|ai|technologies|the)\b\.?', ' ', n) if len(n.split()) > 1 else n
    words = re.findall(r'[a-z0-9]+', n)
    if not words:
        return []
    g = [''.join(words), '-'.join(words), words[0]]
    return list(dict.fromkeys(x for x in g if len(x) >= 3))


def funded():
    rows = list(csv.DictReader(open(os.path.join(HERE, 'funded.csv'))))
    seen, out = set(), []
    for r in rows:
        k = r['company'].strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append({'company': r['company'].strip(), 'round': r['round'], 'amount_m': r['amount_m'],
                        'date': r['date'], 'source': r['source']})
    return out


def main():
    companies = funded()
    probes = {(s, a) for s in KNOWN for a in ATS}
    for c in companies:
        c['guesses'] = slug_guesses(c['company'])
        probes |= {(s, a) for s in c['guesses'] for a in ATS}
    probes = sorted(probes)
    print(f'{len(KNOWN)} known boards, {len(companies)} funded companies, {len(probes)} probes', file=sys.stderr)
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda p: ATS[p[1]](p[0]), probes))
    boards = {f'{a}:{s}': r for (s, a), r in zip(probes, res) if r is not None}
    errors = sorted(k for k, v in boards.items() if v == 'error')
    snap = {'fetched_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
            'known': KNOWN, 'funded': companies, 'errors': errors,
            'boards': {k: v for k, v in boards.items() if v != 'error'}}
    json.dump(snap, open(OUT, 'w'))
    print(f'{len(snap["boards"])} live boards, {sum(len(b["jobs"]) for b in snap["boards"].values())} postings, '
          f'{len(errors)} errors -> {OUT}', file=sys.stderr)


if __name__ == '__main__':
    main()
