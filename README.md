# Who is actually hiring?

```
python3 fetch.py     # (data/ is not committed; run this first) snapshot Ashby / Greenhouse / Lever public boards -> data/snapshot.json (about a minute)
python3 analyze.py   # every number below, stdlib only, 0.2 seconds
```

Snapshot 14 Oct 2026. Two inputs: 172 job boards I maintain by hand for my own job search, and 141 company
names my funding scout pulled from funding headlines, 5-13 Oct 2026. Every match was labeled by hand.

1. **Funding news to job board.** A name-based resolver (squashed, hyphenated, first word; Ashby, Greenhouse, Lever)
   attached a board to 48 names: 29 right, 13 wrong, 6 consistent but unconfirmed. 263 postings went to the wrong
   company (Parallel Systems, $100M freight rail -> Parallel Web Systems' 26 jobs; Noah, stablecoin payments ->
   an animal hospital). No first-word fallback + abstain when a slug is live on 2+ ATSs: 34 attached, 2 wrong,
   3 right lost; precision 69% -> 93%. The round amount quoted in job posts confirms 5/29 right, 0/13 wrong.
2. **One slug, several companies.** Of the 172 hand-checked slugs, 14 also answer on another ATS: 5 are different
   companies (93 postings; `greenhouse:lovable` is an Italian lingerie brand), Mesh posts the same 17 jobs on both,
   Orb keeps 3 "Sample Job" posts from 2023, Vercel's Ashby board is empty with 89 jobs on Greenhouse.
3. **Postings are not hires.** 7,790 postings, 162 companies: median age 54 days, 31.5% over 90 days, 14.4% repeat
   titles, 27.2% of Ashby posts list extra cities.

## The part I got wrong
My scout watched Vercel's empty Ashby board; my dead-board check only looked for 404s.

Syed Ahmed Basharat Ali · basharat.net
