"""Every number in the README, from data/snapshot.json. Stdlib only, under a second.

usage: python3 analyze.py
Hand labels below were made by reading each board's own "About us" text against the funding headline
(and, where the headline was missing, the company's press coverage). They are the ground truth here.
"""
import collections, datetime as dt, json, os, re, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, 'data', 'snapshot.json')))
B, KNOWN, FUNDED = S['boards'], S['known'], S['funded']
NOW = dt.datetime.fromisoformat(S['fetched_utc'])
ORDER = ('ashby', 'greenhouse', 'lever')

# Boards that answer to one of my hand-checked slugs on a different ATS.
CROSS = {
    'greenhouse:profound': ('other', 'ProFound Therapeutics (biotech), not Profound (AI search)'),
    'greenhouse:lovable': ('other', 'Lovable, an Italian lingerie brand, not Lovable (AI app builder)'),
    'greenhouse:handshake': ('other', 'Pioneer Consulting'),
    'greenhouse:hazel': ('other', 'Hazel Health (school mental health), not Hazel (AI for consumer brands)'),
    'greenhouse:socket': ('other', 'Socket Labs (blockchain), not Socket (open-source security)'),
    'greenhouse:mesh': ('same, duplicate', 'Mesh posts the same 17 jobs on Ashby and Greenhouse'),
    'greenhouse:orb': ('same, stale', 'Orb: 1 live job plus 3 "Sample Job" postings from Feb 2023'),
    'greenhouse:vercel': ('same, moved', 'Vercel: 89 jobs here; the Ashby board I watched is empty'),
}

# Funding-news name -> {board: label}. right = same company; wrong = a different company;
# consistent = board text fits the round's sector but I did not confirm identity; empty boards are unlabeled.
FL = {
    'Gallatin AI': {'ashby:gallatin': 'right'}, 'Gallatin': {'ashby:gallatin': 'right'},
    'Vitalize': {'ashby:vitalize': 'right'}, 'Vesta': {'ashby:vesta': 'right'},
    'Nous Research': {'ashby:nousresearch': 'right', 'ashby:nous': 'wrong'},
    'Veir': {'greenhouse:veir': 'right'}, 'Avarra': {'ashby:avarra': 'consistent'},
    'Siena': {'ashby:siena': 'right'}, 'Siena AI': {'ashby:siena': 'right'},
    'Healthleap': {'ashby:healthleap': 'right'}, 'Vocca': {'ashby:vocca': 'right'},
    'Ampersand': {'ashby:ampersand': 'consistent'}, 'Arena': {'ashby:arena': 'right'},
    'Sequoia-backed Catalyst': {'ashby:sequoia': 'wrong'},
    'General Medicine': {'ashby:general-medicine': 'right', 'greenhouse:general': 'wrong'},
    'Outmarket AI': {'ashby:outmarket': 'consistent'}, 'Quartermaster': {'ashby:quartermaster': 'right'},
    'Valon': {'ashby:valon': 'right'}, 'Valon Technologies': {'ashby:valon': 'right'},
    "Taiwan's KONST": {'greenhouse:taiwan': 'wrong'},
    'Hone': {'ashby:hone': 'right', 'greenhouse:hone': 'wrong'},
    'TrueLayer': {'greenhouse:truelayer': 'right'}, 'Melius': {'ashby:melius': 'consistent'},
    'Meticulous': {'ashby:meticulous': 'right'}, 'Sabi': {'ashby:sabi': 'right'},
    'Crypto prop trading startup Vest': {'lever:crypto': 'wrong'}, 'Restate': {'ashby:restate': 'right'},
    'Vinci Pharmaceuticals': {'ashby:vinci': 'wrong'}, 'Vinci': {'ashby:vinci': 'right'},
    'Oratomic': {'ashby:oratomic': 'consistent'}, 'Flow Engineering': {'ashby:flowengineering': 'right'},
    'Gardens Interactive': {'ashby:gardens': 'right'},
    'Golf media startup Pro Shop': {'greenhouse:golf': 'wrong'},
    'Parallel Systems': {'ashby:parallel': 'wrong', 'greenhouse:parallel': 'right'},
    'Parallel': {'ashby:parallel': 'wrong', 'greenhouse:parallel': 'right'},
    'Autonomous freight rail startup Parallel': {'lever:autonomous': 'wrong'},
    'Preference Model': {'ashby:preference-model': 'right'}, 'Owkin alum': {'ashby:owkin': 'wrong'},
    'Dutch cybersecurity firm Hadrian': {'lever:dutch': 'wrong'}, 'Noah': {'greenhouse:noah': 'wrong'},
    'Ultra': {'ashby:ultra': 'wrong'}, 'Clueso': {'ashby:clueso': 'right'}, 'Scarlet': {'ashby:scarlet': 'consistent'},
    'Brellium': {'ashby:brellium': 'right'}, 'CScale': {'greenhouse:cscale': 'right'},
    'Causa Prima': {'ashby:causaprima': 'right'}, 'Reach Security': {'ashby:reach': 'right'},
    'Plaud Alum': {'ashby:plaud': 'wrong'},
}
WHY_WRONG = {
    'Parallel Systems': 'raised a $100M Series C for autonomous freight rail; ashby:parallel is Parallel Web Systems',
    'Hone': 'raised a $60M seed for outcome-owning agents; greenhouse:hone is a people-development platform',
    'Golf media startup Pro Shop': 'headline parsing kept "Golf"; greenhouse:golf is GOLF.com',
    'Ultra': 'warehouse packing robots; ashby:ultra sells nicotine-free pouches',
    'Noah': 'stablecoin payments; greenhouse:noah is North Oatlands Animal Hospital',
    'Crypto prop trading startup Vest': 'headline parsing kept "Crypto"; lever:crypto has 87 jobs',
    'Plaud Alum': 'the alum founded Ambi; ashby:plaud is Plaud itself, 52 jobs',
}


def live(k):
    return k in B and len(B[k]['jobs']) > 0


def age(p):
    try:
        return (NOW - dt.datetime.fromisoformat(p.replace('Z', '+00:00'))).days
    except Exception:
        return None


def title_key(t):
    t = re.sub(r'\(.*?\)', '', t.lower())
    t = re.sub(r'\s[-|,]\s*(remote|hybrid|nyc|new york|san francisco|sf|london|us|usa|united states|emea|apac).*$', '', t)
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()


def pct(a, b):
    return f'{100 * a / b:.1f}%'


def resolve(c, careful=False):
    """Naive: first live board over guesses (squashed, hyphenated, first word) x ATS order.
    Careful: skip the first-word fallback for multi-word names, and abstain when a slug is live on 2+ ATSs."""
    guesses = c['guesses']
    if careful and len(guesses) > 1 and len(c['company'].split()) > 1:
        guesses = guesses[:2]
    for g in guesses:
        hits = [f'{a}:{g}' for a in ORDER if live(f'{a}:{g}')]
        if not hits:
            continue
        if careful and len(hits) > 1:
            return 'abstain'
        return hits[0]
    return None


def main():
    print(f'Snapshot {S["fetched_utc"]}: {len(B)} live boards, {sum(len(b["jobs"]) for b in B.values()):,} postings')

    # 1. One slug, several companies
    own = [f'{a}:{k}' for k, a in KNOWN.items() if k in KNOWN and f'{a}:{k}' in B]
    print(f'\n1. Hand-checked boards: {len(KNOWN)} slugs, {len(own)} answer on their own ATS')
    cross = [f'{o}:{k}' for k, a in KNOWN.items() for o in ORDER if o != a and f'{o}:{k}' in B]
    shells = [x for x in cross if not B[x]['jobs']]
    print(f'   Same slug also answers on another ATS: {len(cross)} ({len(shells)} empty Lever shells)')
    for k, (lab, why) in CROSS.items():
        print(f'   {k:24s} {len(B[k]["jobs"]):3d} jobs  {lab:16s} {why}')
    other = [k for k, (lab, _) in CROSS.items() if lab == 'other']
    print(f'   -> {len(other)} slugs belong to a different company, carrying '
          f'{sum(len(B[k]["jobs"]) for k in other)} postings')
    empty_own = [k for k in own if not B[k]['jobs']]
    print(f'   My own list: {len(empty_own)} of {len(own)} boards return 0 jobs '
          f'({", ".join(x.split(":")[1] for x in empty_own)}); Vercel has '
          f'{len(B["greenhouse:vercel"]["jobs"])} on Greenhouse')
    m_a = {j['title'].strip().lower() for j in B['ashby:mesh']['jobs']}
    m_g = {j['title'].strip().lower() for j in B['greenhouse:mesh']['jobs']}
    print(f'   Mesh: {len(m_a)} titles on Ashby, {len(m_g)} on Greenhouse, {len(m_a & m_g)} identical')

    # 2. Funding news -> job board
    print(f'\n2. Funding news, Oct 5-13 2026: {len(FUNDED)} company names from headlines')
    lab = lambda c, k: FL.get(c['company'], {}).get(k, 'unlabeled')
    for mode in (False, True):
        res = [(c, resolve(c, mode)) for c in FUNDED]
        att = [(c, k) for c, k in res if k and k != 'abstain']
        cnt = collections.Counter(lab(c, k) for c, k in att)
        ab = sum(1 for _, k in res if k == 'abstain')
        name = 'careful' if mode else 'naive  '
        print(f'   {name}: attached {len(att)}, right {cnt["right"]}, wrong {cnt["wrong"]}, '
              f'consistent-unverified {cnt["consistent"]}, unlabeled {cnt["unlabeled"]}, abstained {ab}; '
              f'wrong postings {sum(len(B[k]["jobs"]) for c, k in att if lab(c, k) == "wrong")}')
        if not mode:
            naive_wrong = [(c['company'], k, len(B[k]['jobs'])) for c, k in att if lab(c, k) == 'wrong']
        else:
            careful_wrong = [(c['company'], k) for c, k in att if lab(c, k) == 'wrong']
            lost = [(c['company'], r) for (c, r), (_, k) in zip(res, [(c, resolve(c)) for c in FUNDED])
                    if lab(c, k) == 'right' and (r is None or r == 'abstain')]
    for n, k, j in naive_wrong:
        print(f'     naive wrong: {n:38s} -> {k:22s} {j:3d} jobs  {WHY_WRONG.get(n, "")}')
    print(f'   careful still wrong: {careful_wrong}')
    print(f'   careful lost (right under naive, now abstain/none): {lost}')
    conf = collections.Counter()
    for c in FUNDED:
        k = resolve(c)
        if k and k != 'abstain' and c['amount_m']:
            txt = ' '.join(j['text'] for j in B[k]['jobs']).lower()
            s = '%g' % float(c['amount_m'])
            said = any(p in txt for p in (f'${s}m', f'${s} m', f'${s} million', f'{s} million', f'${s}mm'))
            conf[(lab(c, k), said)] += 1
    print(f'   Second key, the round amount quoted in the job posts: right {conf[("right", True)]}/'
          f'{conf[("right", True)] + conf[("right", False)]}, wrong {conf[("wrong", True)]}/'
          f'{conf[("wrong", True)] + conf[("wrong", False)]}')
    hone = {a: live(f'{a}:hone') for a in ORDER}
    print(f'   ATS order matters: "hone" is live on {[a for a, v in hone.items() if v]}; Ashby-first is right, '
          f'Greenhouse-first is wrong')
    core = collections.defaultdict(list)
    for c in FUNDED:
        k = re.sub(r'\b(ai|technologies|systems|inc)\b', '', c['company'].lower())
        k = re.sub(r'^.*\b(startup|firm|backed)\s+', '', k).strip()
        core[re.sub(r'[^a-z0-9]', '', k)].append(c['company'])
    dups = {k: v for k, v in core.items() if len(v) > 1}
    print(f'   Same company under several headline names: {dups}')

    # 3. Postings are not hires
    P = [(k, j) for k, a in KNOWN.items() if live(f'{a}:{k}') for j in B[f'{a}:{k}']['jobs']]
    cos = {k for k, _ in P}
    ages = [x for x in (age(j['published']) for _, j in P) if x is not None]
    print(f'\n3. Postings on my hand-checked boards: {len(P):,} across {len(cos)} companies')
    print(f'   Age: median {st.median(ages):.0f} days; >90d {pct(sum(x > 90 for x in ages), len(ages))}, '
          f'>180d {pct(sum(x > 180 for x in ages), len(ages))}, >365d {pct(sum(x > 365 for x in ages), len(ages))}')
    per = collections.defaultdict(collections.Counter)
    for k, j in P:
        per[k][title_key(j['title'])] += 1
    distinct = sum(len(c) for c in per.values())
    print(f'   Distinct titles per company: {distinct:,}; repeat copies {len(P) - distinct:,} '
          f'({pct(len(P) - distinct, len(P))})')
    top = sorted(((v, k, t) for k, c in per.items() for t, v in c.items()), reverse=True)[:3]
    print(f'   Most repeated: {top}')
    sec = sum(1 for k, j in P if KNOWN[k] == 'ashby' and j['secondary'])
    ash = sum(1 for k, j in P if KNOWN[k] == 'ashby')
    print(f'   Ashby postings that list extra cities on one post: {sec:,} of {ash:,} ({pct(sec, ash)})')
    ratio = sorted(((sum(c.values()) / len(c), k, sum(c.values()), len(c)) for k, c in per.items()
                    if sum(c.values()) >= 30), reverse=True)
    print(f'   Postings per distinct title, companies with 30+ postings: max {ratio[0][1]} {ratio[0][0]:.2f} '
          f'({ratio[0][2]}/{ratio[0][3]}), min {ratio[-1][1]} {ratio[-1][0]:.2f}')
    by_post = [k for k, _ in sorted(((k, sum(c.values())) for k, c in per.items()), key=lambda x: -x[1])[:10]]
    by_role = [k for k, _ in sorted(((k, len(c)) for k, c in per.items()), key=lambda x: -x[1])[:10]]
    new30 = collections.Counter(k for k, j in P if (age(j['published']) or 999) <= 30)
    new30r = collections.Counter()
    for k in cos:
        new30r[k] = len({title_key(j['title']) for kk, j in P if kk == k and (age(j['published']) or 999) <= 30})
    t_post = [k for k, _ in new30.most_common(10)]
    t_role = [k for k, _ in new30r.most_common(10)]
    print(f'   Top 10 by open postings vs by distinct titles share {len(set(by_post) & set(by_role))} companies')
    print(f'   "Hiring fastest" (new in 30 days), top 10 by postings vs by distinct titles share '
          f'{len(set(t_post) & set(t_role))}: {t_post} vs {t_role}')


if __name__ == '__main__':
    main()
