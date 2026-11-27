// 0.23 : la famille d'un arbre (tel que rendu par /api/arbre ou /api/invite/…/arbre), prête pour les vues :
// parents, enfants, conjoints, fratrie, père et mère, et quelques mots pour l'affichage.

export function famille(arbre) {
  const P = new Map(arbre.personnes.map((p) => [p.id, p]))
  const parents = new Map(), enfants = new Map(), conjoints = new Map(), ex = new Set(), freres = new Map()
  const ajouter = (m, a, b) => { const l = m.get(a) || m.set(a, []).get(a); if (!l.includes(b)) l.push(b) }
  for (const l of arbre.liens) {
    if (!P.has(l.de) || !P.has(l.vers)) continue
    if (l.type === 'parent') { ajouter(parents, l.vers, l.de); ajouter(enfants, l.de, l.vers) }
    else if (l.type === 'conjoint') {
      ajouter(conjoints, l.de, l.vers); ajouter(conjoints, l.vers, l.de)
      if (l.divorce) { ex.add(l.de + '|' + l.vers); ex.add(l.vers + '|' + l.de) }
    } else if (l.type === 'fratrie') { ajouter(freres, l.de, l.vers); ajouter(freres, l.vers, l.de) }
  }
  const de = (m, id) => m.get(id) || []
  const fratrie = (id) => {
    const s = new Set(de(freres, id))
    for (const p of de(parents, id)) for (const e of de(enfants, p)) if (e !== id) s.add(e)
    return [...s]
  }
  // Père et mère d'après le genre ; genre inconnu : le premier parent à gauche
  const pereMere = (id) => {
    const ps = de(parents, id)
    let pere = ps.find((x) => P.get(x).genre === 'homme') || null
    let mere = ps.find((x) => P.get(x).genre === 'femme' && x !== pere) || null
    for (const x of ps) { if (x === pere || x === mere) continue; if (!pere) pere = x; else if (!mere) mere = x }
    return [pere, mere]
  }
  return { P, parents: (id) => de(parents, id), enfants: (id) => de(enfants, id), conjoints: (id) => de(conjoints, id),
           ex: (a, b) => ex.has(a + '|' + b), fratrie, pereMere }
}

export const masquee = (p) => p?.statut === 'masque'
export const nomDe = (p) => (masquee(p) ? 'Personne non montrée' : p?.nom || 'Sans nom')
export function prenomNom(p) {
  if (masquee(p)) return ['Non montrée', '']
  const m = (p?.nom || '').trim().split(/\s+/)
  return [m[0] || 'Sans nom', m.slice(1).join(' ')]
}
export function initiales(p) {
  if (masquee(p)) return '·'
  const m = (p?.nom || '').trim().split(/\s+/).filter(Boolean)
  return ((m[0]?.[0] || '') + (m.length > 1 ? m.at(-1)[0] : '')).toUpperCase() || '·'
}
export function annees(p) {
  if (!p || masquee(p)) return ''
  const n = (p.naissance || '').slice(0, 4), d = p.deces === 'inconnue' ? '†' : (p.deces || '').slice(0, 4)
  return n && d ? `${n}–${d}` : n ? n : d ? (d === '†' ? '†' : `† ${d}`) : ''
}
export function teinte(texte) { let h = 0; for (const c of texte || '?') h = (h * 31 + c.charCodeAt(0)) >>> 0; return h % 360 }

// ---------------------------------------------------------------- chemin entre deux personnes (0.23)
// Le plus court par le sang (parents, enfants, frères et sœurs) ; s'il n'y en a pas, en passant aussi par les couples.
// Rend les étapes depuis `a` : [{ id, rel }] avec rel = parent | enfant | frere | conjoint (la première étape est `a`).
export function chemin(fam, a, b) {
  if (!a || !b || a === b) return null
  const voisins = (x, alliance) => {
    const v = [...fam.parents(x).map((y) => [y, 'parent']), ...fam.enfants(x).map((y) => [y, 'enfant']),
               ...fam.fratrie(x).map((y) => [y, 'frere'])]
    if (alliance) v.push(...fam.conjoints(x).map((y) => [y, 'conjoint']))
    return v
  }
  for (const alliance of [false, true]) {
    const avant = new Map([[a, null]]), file = [a]
    while (file.length) {
      const x = file.shift()
      if (x === b) break
      for (const [y, rel] of voisins(x, alliance)) if (!avant.has(y)) { avant.set(y, [x, rel]); file.push(y) }
    }
    if (!avant.has(b)) continue
    const etapes = []
    for (let x = b; x !== a; x = avant.get(x)[0]) etapes.unshift({ id: x, rel: avant.get(x)[1] })
    etapes.unshift({ id: a, rel: null })
    // « sa mère, puis son fils » vers un enfant de ce parent = « son frère » (même parent)
    for (let i = 1; i + 1 < etapes.length; i++) {
      if (etapes[i].rel === 'parent' && etapes[i + 1].rel === 'enfant' && fam.fratrie(etapes[i - 1].id).includes(etapes[i + 1].id)) {
        etapes.splice(i, 2, { id: etapes[i + 1].id, rel: 'frere' })
      }
    }
    return { etapes, alliance }
  }
  return null
}

// « sa mère Marie », « son fils Paul » : la personne d'une étape, vue depuis la précédente
export function motEtape(fam, e, precedente) {
  const p = fam.P.get(e.id), g = p?.genre
  const f = (fe, ho, ne) => (g === 'femme' ? fe : g === 'homme' ? ho : ne)
  const mot = e.rel === 'parent' ? f('sa mère', 'son père', 'son parent')
    : e.rel === 'enfant' ? f('sa fille', 'son fils', 'son enfant')
    : e.rel === 'frere' ? f('sa sœur', 'son frère', 'son frère ou sa sœur')
    : fam.ex(precedente, e.id) ? f('son ex-conjointe', 'son ex-conjoint', 'son ex-conjoint·e') : f('sa conjointe', 'son conjoint', 'son conjoint·e')
  return `${mot} ${masquee(p) ? '(personne non montrée)' : prenomNom(p)[0]}`
}

// Les personnes et les liens d'un chemin, pour le surligner
export function surlignage(ch) {
  if (!ch) return null
  const ids = new Set(ch.etapes.map((e) => e.id)), aretes = new Set()
  for (let i = 1; i < ch.etapes.length; i++) { const a = ch.etapes[i - 1].id, b = ch.etapes[i].id; aretes.add(a + '|' + b); aretes.add(b + '|' + a) }
  return { ids, aretes }
}
