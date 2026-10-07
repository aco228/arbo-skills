// Meta Ad Library extractor: body of an async function(KNOWN: Set, LIMIT, DOMAIN).
// Never paste by hand: `sync.py js <competitor>` (next to this file) prints the
// install snippet (stores this body in the tab's window.name) and the short
// per-competitor call. Scrolls until LIMIT cards are loaded (or no more load),
// then returns only ads not yet in the db plus the ids of known ads it saw.
// DOMAIN: lowercased domain to keep, or null (page-based competitor).

const idSpans = () => [...document.querySelectorAll('span')]
  .filter(e => e.childElementCount === 0 && /^Library ID: \d+$/.test(e.textContent.trim()));

const t0 = Date.now();
let prev = idSpans().length, stale = 0;
while (stale < 3 && prev < LIMIT && Date.now() - t0 < 50000) {
  window.scrollTo(0, document.body.scrollHeight);
  await new Promise(r => setTimeout(r, 1500));
  const c = idSpans().length;
  stale = c === prev ? stale + 1 : 0;
  prev = c;
}

const cardOf = el => {
  let n = el;
  while (n.parentElement && (n.parentElement.innerText.match(/Library ID:/g) || []).length === 1) n = n.parentElement;
  return n;
};
const landing = href => {
  try {
    const u = new URL(href);
    const real = u.hostname.endsWith('facebook.com') && u.pathname === '/l.php' ? u.searchParams.get('u') : href;
    const r = new URL(real);
    return r.origin + r.pathname;
  } catch (e) { return null; }
};

const seenKnown = [], fresh = [];
let offDomain = 0;
for (const [idx, span] of idSpans().slice(0, LIMIT).entries()) {
  const id = span.textContent.trim().replace('Library ID: ', '');
  if (KNOWN.has(id)) { seenKnown.push(id); continue; }
  const card = cardOf(span);
  const texts = [];
  const w = document.createTreeWalker(card, NodeFilter.SHOW_TEXT);
  let t;
  while ((t = w.nextNode())) {
    const s = t.textContent.trim();
    if (s && s !== '​') texts.push({ s, a: t.parentElement.closest('a')?.href || '' });
  }
  const all = texts.map(x => x.s);
  const status = all.includes('Active') ? 'active' : (all.includes('Inactive') ? 'inactive' : null);
  const run = all.find(s => /^Started running on /.test(s) || /^\d{1,2} \w{3} \d{4} - \d{1,2} \w{3} \d{4}$/.test(s)) || null;
  const iSp = all.indexOf('Sponsored');
  const page = iSp > 0 ? texts[iSp - 1] : null;
  const after = iSp >= 0 ? texts.slice(iSp + 1) : [];
  const linkIdx = after.findIndex(x => /l\.facebook\.com\/l\.php|^https?:\/\/(?!www\.facebook\.com)/.test(x.a));
  const primary = (linkIdx >= 0 ? after.slice(0, linkIdx) : after).map(x => x.s).join('\n');
  const link = linkIdx >= 0 ? after.slice(linkIdx).filter(x => x.a === after[linkIdx].a).map(x => x.s) : [];
  const url = linkIdx >= 0 ? landing(after[linkIdx].a) : null;
  const domain = link[0] ? link[0].toLowerCase() : null;
  if (DOMAIN && !((domain || '').includes(DOMAIN) || (url || '').toLowerCase().includes(DOMAIN))) { offDomain++; continue; }
  fresh.push({
    library_id: id,
    rank: idx + 1, // position in the impressions-sorted list
    status,
    run_text: run,
    page_name: page ? page.s : null,
    page_url: page ? page.a : null,
    page_id: page && (page.a.match(/facebook\.com\/(\d+)\/?$/) || [])[1] || null,
    primary_text: primary || null,
    domain,
    headline: link[1] || null,
    description: link.length > 3 ? link.slice(2, -1).join('\n').slice(0, 200) : null,
    cta: link.length > 2 ? link[link.length - 1] : null,
    landing_url: url,
    multiple_versions: /multiple versions/i.test(card.innerText),
  });
}
// Compact TSV (one ad per line) keeps the handoff cheap; `sync.py merge` reads it.
const clean = v => (v == null ? '' : String(v)).replace(/[\t\n]+/g, ' ').replace(/ ?\d:\d\d \/ \d:\d\d/g, '').trim();
return [`#loaded=${idSpans().length} off_domain=${offDomain} known=${seenKnown.join(',')}`,
 ...fresh.map(a => [a.library_id, a.rank, (a.run_text || '').replace('Started running on ', ''), a.page_name,
   a.headline, a.landing_url, (a.primary_text || '').slice(0, 120), a.page_id].map(clean).join('\t'))].join('\n')
