#!/usr/bin/env python3
"""Local competitor-ad db for the arbo-competitor-scout skill (Meta Ad Library pulls).

The skill folder is read-only (it is updated by pulling the shared arbo-skills
repo). Everything this script writes goes to the user's own data folder:
  --data DIR  >  $ARBO_COMPETITORS_DIR  >  ./competitors  (in the current folder)
It is created on first use and seeded with competitors.seed.json.

  sync.py init                                  # create the data folder (also done automatically)
  sync.py list [--all]                          # competitors, ads pulled, last scan
  sync.py add <domain | page id | page name | Ad Library / page URL> [--page-name] [--id ID] [--country CC] [--note TEXT]
  sync.py pages [--name TEXT] [--competitor C]  # Facebook pages seen in pulled ads (name -> page id)
  sync.py resolve <competitor> <page id>        # set the page id of a competitor added by page name
  sync.py drop <competitor> [--reason TEXT]     # no ads in the library -> never scan again
  sync.py url <competitor>
  sync.py js <competitor> [--limit N] [--mode run|install|both|resolve]   # browser snippets
  sync.py merge <competitor> <result file>      # extractor output -> db, logs the scan
  sync.py scans [--competitor C] [--limit N]    # scan history
  sync.py pending [--competitor C] [--min-days N] [--limit N]
  sync.py mark <library_id> [...] [--vertical V] [--angle TEXT] [--note TEXT]
  sync.py verticals <get_verticals.json>        # refresh the division's vertical list
  sync.py ideas [--vertical V] [--limit N]      # analysed articles not used for titles yet
  sync.py rec-list [--vertical V] [--country C]
  sync.py rec-log <submitted.json>              # after a successful submit
  sync.py stats
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

SKILL_DIR = Path(__file__).resolve().parent
EXTRACT_JS = SKILL_DIR / "extract.js"
SEED = SKILL_DIR / "competitors.seed.json"
NO_VERTICAL = "none"
DEFAULT_LIMIT = 100
DEFAULT_MIN_DAYS = 7

# Set in main() once the data folder is resolved.
DATA = COMPETITORS = DB = RECS = SCANS = VERTICALS = None


def resolve_data(arg):
    data = Path(arg or os.environ.get("ARBO_COMPETITORS_DIR") or Path.cwd() / "competitors").expanduser().resolve()
    # The skill lives in a shared repo that users only pull; writing there causes conflicts.
    skills_repo = SKILL_DIR.parent.parent
    if data == skills_repo or skills_repo in data.parents or SKILL_DIR in data.parents:
        sys.exit(f"refusing to write into the shared skills folder ({skills_repo}). "
                 "Run from your own project folder or pass --data <your folder>.")
    return data


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    tmp.replace(path)


def ensure_init(verbose=False):
    if COMPETITORS.exists():
        if verbose:
            print(f"data folder: {DATA} (exists)")
        return
    seed = load(SEED, {"competitors": []})
    for c in seed["competitors"]:
        c.setdefault("last_sync", None)
    save(COMPETITORS, seed)
    for sub in ("db", "drafts", "insights"):
        (DATA / sub).mkdir(parents=True, exist_ok=True)
    print(f"created data folder {DATA} with {len(seed['competitors'])} seed competitors")


def competitors():
    return load(COMPETITORS, {"competitors": []})


def competitor(cid):
    for c in competitors()["competitors"]:
        if c["id"] == cid:
            return c
    sys.exit(f"unknown competitor '{cid}' (see `list --all`, or `add` it)")


def library_url(c):
    if c.get("page_name") and not c.get("page_id"):
        # Unresolved page name: a keyword search page, only to get the Ad Library search box for `js --mode resolve`.
        return ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL"
                f"&is_targeted_country=false&media_type=all&q={quote(c['page_name'])}&search_type=keyword_unordered")
    base = ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
            f"&country={c.get('country', 'ALL')}&is_targeted_country=false&media_type=all"
            "&sort_data[mode]=total_impressions&sort_data[direction]=desc")
    if c.get("page_id"):
        return base + f"&search_type=page&view_all_page_id={c['page_id']}"
    return base + f"&q={quote(c.get('query') or c['domain'])}&search_type=keyword_unordered"


def parse_run(text):
    """'Started running on 21 Sep 2026' or '1 Sep 2026 - 20 Sep 2026' -> (start, end)."""
    if not text:
        return None, None
    days = []
    for d in re.findall(r"\d{1,2} \w{3} \d{4}", text):
        try:
            days.append(datetime.strptime(d, "%d %b %Y").date().isoformat())
        except ValueError:
            days.append(None)
    return (days[0] if days else None), (days[1] if len(days) > 1 else None)


def language(url):
    if not url:
        return None
    path = urlparse(url).path
    seg = path.strip("/").split("/")[0]
    if re.fullmatch(r"[a-z]{2}(-[a-z]{2})?", seg or ""):
        return seg
    m = re.search(r"[-_]lang-([a-z]{2})\b", path)
    return m.group(1) if m else None


def days_running(ad, today):
    if not ad.get("start_date"):
        return None
    end = ad.get("end_date") or ad.get("last_seen") or today
    return (date.fromisoformat(end) - date.fromisoformat(ad["start_date"])).days


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def cmd_init(_):
    ensure_init(verbose=True)


def label(c):
    if c.get("page_id"):
        return f"page {c['page_id']}" + (f" ({c['page_name']})" if c.get("page_name") else "")
    if c.get("page_name"):
        return f"page name '{c['page_name']}' (unresolved)"
    return c.get("domain")


def seen_pages(db, name=None):
    """{page_id: {"names": set, "ads": n, "competitors": set}} from pulled ads, optionally only exact (casefold) name matches."""
    pages = {}
    for ad in db.values():
        pid, pn = ad.get("page_id"), ad.get("page_name")
        if not pid or (name and (pn or "").casefold() != name.casefold()):
            continue
        p = pages.setdefault(pid, {"names": set(), "ads": 0, "competitors": set()})
        p["names"].add(pn)
        p["ads"] += 1
        p["competitors"].add(ad["competitor"])
    return pages


def cmd_list(a):
    db = load(DB, {})
    for c in competitors()["competitors"]:
        if c.get("dropped") and not a.all:
            continue
        n = sum(1 for x in db.values() if x["competitor"] == c["id"])
        print(f"{c['id']:<24} {label(c):<30} ads={n:<5} last_sync={c.get('last_sync')}"
              + (f"  DROPPED {c['dropped']}: {c.get('drop_reason')}" if c.get("dropped") else ""))


def cmd_add(a):
    """Accepts a domain, a numeric page id, a page name, or an Ad Library / Facebook page URL.
    Text without a dot (or with spaces) is a page name; --page-name forces it."""
    target, entry = a.target.strip(), {}
    if a.page_name:
        entry["page_name"] = target
    elif target.startswith("http"):
        u = urlparse(target)
        q = parse_qs(u.query)
        path = [x for x in u.path.split("/") if x]
        if q.get("view_all_page_id"):
            entry["page_id"] = q["view_all_page_id"][0]
        elif q.get("q"):
            entry["domain"] = q["q"][0]
        elif u.hostname and "facebook.com" not in u.hostname:
            entry["domain"] = u.hostname
        elif q.get("id") and q["id"][0].isdigit():  # facebook.com/profile.php?id=...
            entry["page_id"] = q["id"][0]
        elif path and path[0].isdigit():  # facebook.com/<page id>/
            entry["page_id"] = path[0]
        elif path and path[0] not in ("ads", "profile.php", "pages"):  # facebook.com/<username>: resolved like a name
            entry["page_name"] = path[0]
        else:
            sys.exit("can't read a page id, page name or domain from that URL; pass the page id, page name or domain")
    elif target.isdigit():
        entry["page_id"] = target
    elif "." not in target or " " in target:
        entry["page_name"] = target
    else:
        entry["domain"] = target
    if entry.get("domain"):
        entry["domain"] = re.sub(r"^www\.", "", entry["domain"].lower()).rstrip("/")
    if entry.get("page_name"):
        # A name seen on exactly one page in pulled ads is that page; otherwise `js --mode resolve` + `resolve`.
        ids = list(seen_pages(load(DB, {}), entry["page_name"]))
        if len(ids) == 1:
            entry["page_id"] = ids[0]
    comps = competitors()
    for c in comps["competitors"]:
        if ((entry.get("domain") and c.get("domain") == entry["domain"])
                or (entry.get("page_id") and c.get("page_id") == entry["page_id"])
                or (entry.get("page_name") and not entry.get("page_id") and not c.get("page_id")
                    and (c.get("page_name") or "").casefold() == entry["page_name"].casefold())):
            sys.exit(f"already listed as '{c['id']}'" + (" (dropped; sync it by name to retry)" if c.get("dropped") else ""))
    entry["id"] = a.id or slug(entry.get("domain") or entry.get("page_name") or f"page-{entry['page_id']}")
    if any(c["id"] == entry["id"] for c in comps["competitors"]):
        sys.exit(f"id '{entry['id']}' is taken; pass --id")
    if a.country:
        entry["country"] = a.country.upper()
    if a.note:
        entry["notes"] = a.note
    entry["last_sync"] = None
    comps["competitors"].append(entry)
    save(COMPETITORS, comps)
    print(f"added {entry['id']}: {label(entry)}")
    if entry.get("page_name") and not entry.get("page_id"):
        print(f"page id unknown: open `url {entry['id']}`, run `js {entry['id']} --mode resolve`, then `resolve {entry['id']} <page id>`")


def cmd_pages(a):
    db = load(DB, {})
    pages = seen_pages(db, a.name)
    rows = [(pid, p) for pid, p in pages.items() if not a.competitor or a.competitor in p["competitors"]]
    for pid, p in sorted(rows, key=lambda x: -x[1]["ads"]):
        print(f"{pid:<18} ads={p['ads']:<4} {' / '.join(sorted(n or '?' for n in p['names']))}  [{', '.join(sorted(p['competitors']))}]")
    print(f"# pages: {len(rows)}" + ("" if any(ad.get("page_id") for ad in db.values()) else
                                     " (ads pulled before page ids were recorded have none; they fill in on new scans)"))


def cmd_resolve(a):
    if not a.page_id.isdigit():
        sys.exit("page id must be numeric")
    comps = competitors()
    for c in comps["competitors"]:
        if c["id"] != a.competitor and c.get("page_id") == a.page_id:
            sys.exit(f"page {a.page_id} is already listed as '{c['id']}'")
    for c in comps["competitors"]:
        if c["id"] == a.competitor:
            c["page_id"] = a.page_id
            save(COMPETITORS, comps)
            print(f"{c['id']}: {label(c)}")
            return
    sys.exit(f"unknown competitor '{a.competitor}'")


def cmd_drop(a):
    comps = competitors()
    for c in comps["competitors"]:
        if c["id"] == a.competitor:
            c["dropped"] = date.today().isoformat()
            c["drop_reason"] = a.reason
            save(COMPETITORS, comps)
            print(f"dropped {a.competitor}: {a.reason}")
            return
    sys.exit(f"unknown competitor '{a.competitor}'")


def cmd_url(a):
    print(library_url(competitor(a.competitor)))


def cmd_js(a):
    """Prints the browser snippets. The extractor body is stored once in the tab's
    window.name (install; it survives navigation, while Facebook wipes unknown
    localStorage keys), so each sync only sends a short call (run)."""
    c = competitor(a.competitor)
    if a.mode == "resolve":
        if not c.get("page_name"):
            sys.exit(f"'{c['id']}' has no page name to resolve")
        # Types the name into the Ad Library search box and reads the Advertisers suggestions
        # (option ids are `pageID:<id>`). `=` marks an exact name match.
        print("const sleep = ms => new Promise(r => setTimeout(r, ms)); "
              "let inp; for (let i = 0; i < 20 && !(inp = document.querySelector('input[type=search]')); i++) await sleep(500); "
              "if (!inp) 'NO_SEARCH_BOX'; else { inp.focus(); "
              "const type = v => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(inp, v); "
              "inp.dispatchEvent(new Event('input', {bubbles: true})); }; "
              # The box already holds the name from the URL; React ignores a set to the same value, so clear first.
              f"type(''); await sleep(300); type({json.dumps(c['page_name'])}); "
              "let opts = []; for (let i = 0; i < 16 && !opts.length; i++) { await sleep(500); "
              "opts = [...document.querySelectorAll('[role=option][id^=pageID]')]; } "
              "opts.map(o => { const t = o.innerText.split('\\n').map(s => s.trim()).filter(Boolean); "
              f"return [t[0].toLowerCase() === {json.dumps(c['page_name'].lower())} ? '=' : ' ', o.id.slice(7), ...t].join('\\t'); }}).join('\\n') || 'NO_MATCHES'; }}")
        return
    if c.get("page_name") and not c.get("page_id"):
        sys.exit(f"'{c['id']}' has no page id yet: `js {c['id']} --mode resolve`, then `resolve {c['id']} <page id>`")
    known = sorted(i for i, ad in load(DB, {}).items() if ad["competitor"] == c["id"])
    domain = json.dumps(c["domain"].lower()) if c.get("domain") and not c.get("page_id") else "null"
    body = EXTRACT_JS.read_text()
    version = hashlib.sha1(body.encode()).hexdigest()[:8]
    if a.mode in ("install", "both"):
        print(f"window.name = JSON.stringify({{v: '{version}', body: {json.dumps(body)}}}); 'installed {version}'")
    if a.mode in ("run", "both"):
        # Facebook's CSP forbids eval/new Function but allows blob: scripts.
        print("await new Promise(r => setTimeout(r, 2500)); "
              "let ck; try { ck = JSON.parse(window.name); } catch (e) {} "
              f"if (!ck || ck.v !== '{version}') 'REINSTALL'; else {{ "
              "if (window.__ckxv !== ck.v) { await new Promise((ok, bad) => { const s = document.createElement('script'); "
              "s.src = URL.createObjectURL(new Blob(['window.__ckxv = ' + JSON.stringify(ck.v) + '; window.__ckx = async function(KNOWN, LIMIT, DOMAIN) {\\n' + ck.body + '\\n};'], {type: 'text/javascript'})); "
              "s.onload = ok; s.onerror = bad; document.head.appendChild(s); }); } "
              f"await window.__ckx(new Set({json.dumps(known)}), {a.limit}, {domain}); }}")


def read_result(path):
    """Extractor output: TSV (header `#loaded=.. off_domain=.. known=id,id` + one ad per line),
    optionally still JSON-quoted as the browser tool printed it, or legacy JSON."""
    text = path.read_text().strip()
    if text.startswith('"'):
        text = json.loads(text).strip()
    if text.startswith("{"):
        return json.loads(text)
    lines = text.splitlines()
    head = dict(kv.split("=", 1) for kv in lines[0].lstrip("#").split())
    new = []
    for line in lines[1:]:
        f = (line.split("\t") + [""] * 8)[:8]
        new.append({"library_id": f[0], "rank": int(f[1]) if f[1].isdigit() else None,
                    "run_text": f[2] if " - " in f[2] else f"Started running on {f[2]}",
                    "status": "inactive" if " - " in f[2] else "active",
                    "page_name": f[3] or None, "headline": f[4] or None,
                    "landing_url": f[5] or None, "primary_text": f[6] or None, "page_id": f[7] or None})
    return {"loaded": int(head.get("loaded", 0)), "off_domain": int(head.get("off_domain", 0)),
            "seen_known": [i for i in head.get("known", "").split(",") if i], "new": new}


def cmd_merge(a):
    c = competitor(a.competitor)
    if c.get("page_name") and not c.get("page_id"):
        sys.exit(f"'{c['id']}' has no page id yet; resolve it before scanning")
    res = read_result(Path(a.file))
    db = load(DB, {})
    today = date.today().isoformat()
    added = 0
    done_urls = {v.get("landing_url"): v["analyzed"] for v in db.values() if v.get("analyzed") and v.get("landing_url")}
    for ad in res.get("new", []):
        lid = ad["library_id"]
        if lid in db:
            continue
        start, end = parse_run(ad.get("run_text"))
        db[lid] = {
            "competitor": c["id"],
            **{k: v for k, v in ad.items() if k not in ("library_id", "run_text")},
            "start_date": start,
            "end_date": end,
            "language": language(ad.get("landing_url")),
            "first_seen": today,
            "last_seen": today,
            "first_rank": ad.get("rank"),
            "analyzed": done_urls.get(ad.get("landing_url")),  # article already analysed -> skip
        }
        added += 1
    for lid in res.get("seen_known", []):
        if lid in db:
            db[lid]["last_seen"] = today
            db[lid]["status"] = "active"
    save(DB, db)
    comps = competitors()
    for x in comps["competitors"]:
        if x["id"] == c["id"]:
            x["last_sync"] = today
    save(COMPETITORS, comps)
    total = sum(1 for v in db.values() if v["competitor"] == c["id"])
    scans = load(SCANS, [])
    scans.append({"time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "competitor": c["id"],
                  "url": library_url(c), "loaded": res.get("loaded"), "new": added,
                  "known_seen": len(res.get("seen_known", [])), "off_domain": res.get("off_domain"), "db_total": total})
    save(SCANS, scans)
    print(f"{c['id']}: loaded={res.get('loaded')} new={added} known_seen={len(res.get('seen_known', []))} "
          f"off_domain={res.get('off_domain')} db_total={total}")


def cmd_scans(a):
    rows = [s for s in load(SCANS, []) if not a.competitor or s["competitor"] == a.competitor]
    for s in rows[-a.limit:]:
        print(f"{s['time']} {s['competitor']:<24} loaded={s['loaded']} new={s['new']} known_seen={s['known_seen']} "
              f"off_domain={s['off_domain']} db_total={s['db_total']}")
    print(f"# scans: {len(rows)}")


def cmd_pending(a):
    db = load(DB, {})
    today = date.today().isoformat()
    rows = []
    for lid, ad in db.items():
        if ad.get("analyzed") or (a.competitor and ad["competitor"] != a.competitor):
            continue
        d = days_running(ad, today)
        if d is None or d < a.min_days:
            continue
        rows.append((lid, ad, d))
    # one row per article: the same landing page run as many ads / pages is a winner signal
    groups = {}
    for lid, ad, d in rows:
        groups.setdefault(ad.get("landing_url") or lid, []).append((lid, ad, d))
    articles = sorted(groups.values(), key=lambda g: (-len(g), min(x[1].get("first_rank") or 9999 for x in g)))
    young = sum(1 for ad in db.values() if not ad.get("analyzed")
                and (days_running(ad, today) or 0) < a.min_days
                and (not a.competitor or ad["competitor"] == a.competitor))
    print(f"# mature unanalyzed (>= {a.min_days}d): {len(rows)} ads in {len(articles)} articles   still young: {young} ads")
    for g in articles[: a.limit]:
        ad = min(g, key=lambda x: x[1].get("first_rank") or 9999)[1]
        variants = sorted({(x[1].get("headline"), x[1].get("primary_text")) for x in g}, key=str)
        print(json.dumps({"c": ad["competitor"], "lang": ad.get("language"), "ads": len(g),
                          "pages": len({x[1].get("page_name") for x in g}),
                          "max_days": max(x[2] for x in g), "best_rank": ad.get("first_rank"),
                          "url": ad.get("landing_url"),
                          "variants": [{"headline": h, "primary": p} for h, p in variants],
                          "ids": [x[0] for x in g]}, ensure_ascii=False))


def cmd_mark(a):
    db = load(DB, {})
    today = date.today().isoformat()
    if a.vertical and a.vertical != NO_VERTICAL:
        names = {v["name"] for v in load(VERTICALS, [])}
        if names and a.vertical not in names:
            sys.exit(f"unknown vertical '{a.vertical}' (refresh with `verticals`, or use '{NO_VERTICAL}')")
    missing = [i for i in a.ids if i not in db]
    for i in a.ids:
        if i in db:
            db[i]["analyzed"] = today
            for k in ("vertical", "angle", "note"):
                if getattr(a, k):
                    db[i][k] = getattr(a, k)
    save(DB, db)
    print(f"marked {len(a.ids) - len(missing)}" + (f", unknown: {missing}" if missing else ""))


def cmd_verticals(a):
    data = json.loads(Path(a.file).read_text())
    save(VERTICALS, [{"name": v["name"], "description": v.get("description"),
                      "isTopLevel": v.get("isTopLevel", True), "parentVertical": v.get("parentVertical")} for v in data])
    print(f"verticals: {len(data)}")


def article_rows(db, today):
    """Analysed, vertical-tagged ads grouped per article (landing URL)."""
    groups = {}
    for lid, ad in db.items():
        if ad.get("analyzed") and ad.get("vertical") and ad["vertical"] != NO_VERTICAL:
            groups.setdefault(ad.get("landing_url") or lid, []).append((lid, ad))
    rows = []
    for url, g in groups.items():
        best = min(g, key=lambda x: x[1].get("first_rank") or 9999)[1]
        rows.append({
            "vertical": best["vertical"], "c": best["competitor"], "lang": best.get("language"),
            "ads": len(g), "pages": len({x[1].get("page_name") for x in g}),
            "max_days": max(days_running(x[1], today) or 0 for x in g),
            "angle": best.get("angle"), "url": url,
            "headlines": sorted({x[1].get("headline") for x in g if x[1].get("headline")}),
            "primary": best.get("primary_text"),
            "recommended": max((x[1].get("recommended") or "") for x in g) or None,
            "ids": [x[0] for x in g],
        })
    return rows


def cmd_ideas(a):
    today = date.today().isoformat()
    rows = [r for r in article_rows(load(DB, {}), today)
            if not r["recommended"] and (not a.vertical or r["vertical"] == a.vertical)]
    rows.sort(key=lambda r: (r["vertical"], -r["ads"], -r["max_days"]))
    print(f"# unused analysed articles: {len(rows)}")
    for r in rows[: a.limit]:
        r.pop("recommended")
        print(json.dumps(r, ensure_ascii=False))


def cmd_rec_list(a):
    recs = load(RECS, [])
    for r in recs:
        if (a.vertical and r["vertical"] != a.vertical) or (a.country and r["countryCode"].upper() != a.country.upper()):
            continue
        print(f"{r['date']} [{r.get('mode') or 'recommendation'}] {r['vertical']} {r['countryCode']}/{r['languageCode']} "
              f"| {r['title']} | {r['titleInEnglish']}")
    print(f"# total logged: {len(recs)}")


def cmd_rec_log(a):
    """File: {"mode": "recommendation"|"generation", "reference": ..., "tag": ..., "affiliate": ...,
    "titles": [{vertical, countryCode, languageCode, title, titleInEnglish, source_ids: [...]}]}"""
    sub = json.loads(Path(a.file).read_text())
    recs, db = load(RECS, []), load(DB, {})
    today = date.today().isoformat()
    meta = {k: sub.get(k) for k in ("mode", "reference", "tag", "affiliate") if sub.get(k)}
    for t in sub["titles"]:
        recs.append({"date": today, **meta, **t})
        for lid in t.get("source_ids", []):
            if lid in db:
                db[lid]["recommended"] = today
    save(RECS, recs)
    save(DB, db)
    print(f"logged {len(sub['titles'])} titles, total {len(recs)}")


def cmd_stats(_):
    db = load(DB, {})
    today = date.today().isoformat()
    by = {}
    for ad in db.values():
        s = by.setdefault(ad["competitor"], {"ads": 0, "analyzed": 0, "used": 0, "langs": {}, "days": []})
        s["ads"] += 1
        s["analyzed"] += bool(ad.get("analyzed"))
        s["used"] += bool(ad.get("recommended"))
        s["langs"][ad.get("language")] = s["langs"].get(ad.get("language"), 0) + 1
        d = days_running(ad, today)
        if d is not None:
            s["days"].append(d)
    for cid, s in sorted(by.items()):
        days = sorted(s["days"])
        med = days[len(days) // 2] if days else None
        langs = ", ".join(f"{k}:{v}" for k, v in sorted(s["langs"].items(), key=lambda kv: -kv[1])[:8])
        print(f"{cid}: ads={s['ads']} analyzed={s['analyzed']} used_for_titles={s['used']} median_days={med} langs[{langs}]")
    print(f"# data folder: {DATA}")


def main():
    global DATA, COMPETITORS, DB, RECS, SCANS, VERTICALS
    p = argparse.ArgumentParser(description="arbo-competitor-scout local db")
    p.add_argument("--data", help="data folder (default: $ARBO_COMPETITORS_DIR or ./competitors)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(f=cmd_init)
    s = sub.add_parser("list"); s.add_argument("--all", action="store_true", help="include dropped"); s.set_defaults(f=cmd_list)
    s = sub.add_parser("add"); s.add_argument("target"); s.add_argument("--page-name", action="store_true"); s.add_argument("--id"); s.add_argument("--country"); s.add_argument("--note")
    s.set_defaults(f=cmd_add)
    s = sub.add_parser("pages"); s.add_argument("--name"); s.add_argument("--competitor"); s.set_defaults(f=cmd_pages)
    s = sub.add_parser("resolve"); s.add_argument("competitor"); s.add_argument("page_id"); s.set_defaults(f=cmd_resolve)
    s = sub.add_parser("drop"); s.add_argument("competitor"); s.add_argument("--reason", default="no ads in Ad Library"); s.set_defaults(f=cmd_drop)
    s = sub.add_parser("url"); s.add_argument("competitor"); s.set_defaults(f=cmd_url)
    s = sub.add_parser("js"); s.add_argument("competitor"); s.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    s.add_argument("--mode", choices=["run", "install", "both", "resolve"], default="run"); s.set_defaults(f=cmd_js)
    s = sub.add_parser("merge"); s.add_argument("competitor"); s.add_argument("file"); s.set_defaults(f=cmd_merge)
    s = sub.add_parser("scans"); s.add_argument("--competitor"); s.add_argument("--limit", type=int, default=30); s.set_defaults(f=cmd_scans)
    s = sub.add_parser("pending"); s.add_argument("--competitor"); s.add_argument("--min-days", type=int, default=DEFAULT_MIN_DAYS)
    s.add_argument("--limit", type=int, default=100); s.set_defaults(f=cmd_pending)
    s = sub.add_parser("mark"); s.add_argument("ids", nargs="+"); s.add_argument("--vertical"); s.add_argument("--angle")
    s.add_argument("--note"); s.set_defaults(f=cmd_mark)
    s = sub.add_parser("verticals"); s.add_argument("file"); s.set_defaults(f=cmd_verticals)
    s = sub.add_parser("ideas"); s.add_argument("--vertical"); s.add_argument("--limit", type=int, default=100); s.set_defaults(f=cmd_ideas)
    s = sub.add_parser("rec-list"); s.add_argument("--vertical"); s.add_argument("--country"); s.set_defaults(f=cmd_rec_list)
    s = sub.add_parser("rec-log"); s.add_argument("file"); s.set_defaults(f=cmd_rec_log)
    sub.add_parser("stats").set_defaults(f=cmd_stats)
    a = p.parse_args()

    DATA = resolve_data(a.data)
    COMPETITORS = DATA / "competitors.json"
    DB = DATA / "db" / "ads.json"
    RECS = DATA / "db" / "recommendations.json"
    SCANS = DATA / "db" / "scans.json"
    VERTICALS = DATA / "verticals.json"
    if a.cmd != "init":
        ensure_init()
    a.f(a)


if __name__ == "__main__":
    main()
