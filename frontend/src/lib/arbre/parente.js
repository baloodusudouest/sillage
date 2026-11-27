// 0.22 : le lien de parenté entre deux personnes de l'arbre, dit en clair (« Grand-mère », « Cousin »…).
// Calculé d'après les liens parent / conjoint / fratrie, accordé au genre de la personne regardée.

export function indexer(personnes, liens) {
  const parents = new Map(), conjoints = new Map(), ex = new Set(), fratrie = new Map()
  const ajouter = (m, a, b) => (m.get(a) || m.set(a, new Set()).get(a)).add(b)
  for (const l of liens) {
    if (l.type === 'parent') ajouter(parents, l.vers, l.de)
    else if (l.type === 'conjoint') {
      ajouter(conjoints, l.de, l.vers); ajouter(conjoints, l.vers, l.de)
      if (l.divorce) { ex.add(l.de + '|' + l.vers); ex.add(l.vers + '|' + l.de) }
    } else if (l.type === 'fratrie') { ajouter(fratrie, l.de, l.vers); ajouter(fratrie, l.vers, l.de) }
  }
  const genre = new Map(personnes.map((p) => [p.id, p.genre || '']))
  return { parents, conjoints, ex, fratrie, genre }
}

function ancetres(ix, x) {
  const res = new Map(), file = [[x, 0]]
  while (file.length) {
    const [y, d] = file.shift()
    for (const p of ix.parents.get(y) || []) if (!res.has(p)) { res.set(p, d + 1); file.push([p, d + 1]) }
  }
  return res
}

const accord = (g, f, h, n) => (g === 'femme' ? f : g === 'homme' ? h : n)
const arriere = (n) => 'Arrière-'.repeat(n)

export function parente(ix, a, b, profond = 0) {
  if (!a || !b) return ''
  if (a === b) return 'Personne de départ'
  const g = ix.genre.get(b)
  if (ix.conjoints.get(a)?.has(b)) return ix.ex.has(a + '|' + b) ? accord(g, 'Ex-conjointe', 'Ex-conjoint', 'Ex-conjoint·e') : accord(g, 'Conjointe', 'Conjoint', 'Conjoint·e')
  if (ix.fratrie.get(a)?.has(b)) return accord(g, 'Sœur', 'Frère', 'Frère ou sœur')
  const A = ancetres(ix, a), B = ancetres(ix, b)
  if (A.has(b)) {
    const d = A.get(b)
    if (d === 1) return accord(g, 'Mère', 'Père', 'Parent')
    return arriere(d - 2) + accord(g, d > 2 ? 'grand-mère' : 'Grand-mère', d > 2 ? 'grand-père' : 'Grand-père', d > 2 ? 'grand-parent' : 'Grand-parent')
  }
  if (B.has(a)) {
    const d = B.get(a)
    if (d === 1) return accord(g, 'Fille', 'Fils', 'Enfant')
    return arriere(d - 2) + accord(g, d > 2 ? 'petite-fille' : 'Petite-fille', d > 2 ? 'petit-fils' : 'Petit-fils', d > 2 ? 'petit-enfant' : 'Petit-enfant')
  }
  let mieux = null
  for (const [x, da] of A) if (B.has(x)) { const s = da + B.get(x); if (!mieux || s < mieux.s) mieux = { da, db: B.get(x), s, x } }
  if (mieux) {
    const { da, db } = mieux
    if (da === 1 && db === 1) return accord(g, 'Sœur', 'Frère', 'Frère ou sœur')
    if (da === 2 && db === 1) return accord(g, 'Tante', 'Oncle', 'Oncle ou tante')
    if (da === 1 && db === 2) return accord(g, 'Nièce', 'Neveu', 'Neveu ou nièce')
    if (da === 2 && db === 2) return accord(g, 'Cousine', 'Cousin', 'Cousin·e')
    if (da === 3 && db === 1) return accord(g, 'Grand-tante', 'Grand-oncle', 'Grand-oncle ou grand-tante')
    if (da === 1 && db === 3) return accord(g, 'Petite-nièce', 'Petit-neveu', 'Petit-neveu ou petite-nièce')
    if (da === 4 && db === 1) return accord(g, 'Arrière-grand-tante', 'Arrière-grand-oncle', 'Arrière-grand-oncle ou grand-tante')
    if (da === 2 && db === 3) return accord(g, 'Fille de cousin', 'Fils de cousin', 'Enfant de cousin')
    if (da === 3 && db === 2) {                         // 0.23.1 : le cousin d'un parent, en disant lequel
      const x = mieux.x, par = [...(ix.parents.get(a) || [])].find((p) => ancetres(ix, p).get(x) === 2)
      const de = par ? accord(ix.genre.get(par), ' de sa mère', ' de son père', " d'un parent") : " d'un parent"
      return accord(g, 'Cousine', 'Cousin', 'Cousin·e') + de
    }
    if (da === 3 && db === 3) return accord(g, 'Cousine issue de germain', 'Cousin issu de germain', 'Cousin·e issu·e de germain')
    return 'Famille éloignée'
  }
  // Par alliance (un seul détour par un conjoint) : le parent ou le frère du conjoint, le conjoint d'un enfant ou d'un frère
  if (profond) return 'Par alliance'
  for (const c of ix.conjoints.get(a) || []) {
    const via = parente(ix, c, b, 1)
    if (via === 'Mère' || via === 'Père' || via === 'Parent') return accord(g, 'Belle-mère', 'Beau-père', 'Beau-parent')
    if (via === 'Sœur' || via === 'Frère' || via === 'Frère ou sœur') return accord(g, 'Belle-sœur', 'Beau-frère', 'Beau-frère ou belle-sœur')
  }
  // 0.23.1 : la famille de sang du conjoint (sa tante, son cousin…) = « Tante par alliance », « Cousin par alliance »
  for (const c of ix.conjoints.get(a) || []) {
    if (ix.ex.has(a + '|' + c)) continue
    const via = parente(ix, c, b, 1)
    if (via && via !== 'Par alliance' && via !== 'Famille éloignée' && !via.includes(' de ') && !/^(Fille|Fils|Enfant|Petit|Arrière-petit|Ex-|Conjoint)/.test(via)) return via + ' par alliance'
  }
  for (const c of ix.conjoints.get(b) || []) {
    const via = parente(ix, a, c, 1)
    if (via === 'Fille' || via === 'Fils' || via === 'Enfant') return accord(g, 'Belle-fille', 'Gendre', 'Bel enfant')
    if (via === 'Sœur' || via === 'Frère' || via === 'Frère ou sœur') return accord(g, 'Belle-sœur', 'Beau-frère', 'Beau-frère ou belle-sœur')
  }
  return 'Par alliance'
}
