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
    // 0.23.2 (demande de Julien) : on remonte toujours par les parents, jamais « son frère » d'un coup :
    // un frère ou une sœur devient « sa mère, puis sa fille » quand l'arbre connaît un parent commun.
    for (let i = 1; i < etapes.length; i++) {
      if (etapes[i].rel !== 'frere') continue
      const de = etapes[i - 1].id, vers = etapes[i].id
      const communs = fam.parents(de).filter((p) => fam.parents(vers).includes(p))
      if (!communs.length) continue                       // lien « fratrie » seul dans Treemich : on le garde
      const p = communs.find((x) => fam.P.get(x)?.genre === 'femme') || communs[0]
      etapes.splice(i, 1, { id: p, rel: 'parent' }, { id: vers, rel: 'enfant' }); i++
    }
    // 0.23.1 : « sa fille, puis son père » quand ce père est son conjoint = « son conjoint » (on ne passe pas par l'enfant)
    let parAlliance = alliance
    for (let i = 1; i + 1 < etapes.length; i++) {
      const avantId = etapes[i - 1].id, apres = etapes[i + 1]
      if (etapes[i].rel === 'enfant' && apres.rel === 'parent' && fam.conjoints(avantId).includes(apres.id)) {
        etapes.splice(i, 2, { id: apres.id, rel: 'conjoint' }); parAlliance = true; i--
      }
    }
    return { etapes, alliance: parAlliance }
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
export function surlignage(ch, fam = null) {
  if (!ch) return null
  const ids = new Set(ch.etapes.map((e) => e.id)), aretes = new Set()
  const relier = (a, b) => { aretes.add(a + '|' + b); aretes.add(b + '|' + a) }
  for (let i = 1; i < ch.etapes.length; i++) {
    const a = ch.etapes[i - 1].id, b = ch.etapes[i].id
    relier(a, b)
    // 0.23.1 : un frère ou une sœur se rejoint par les parents communs : leurs traits s'allument aussi
    if (fam && ch.etapes[i].rel === 'frere') for (const p of fam.parents(a)) if (fam.parents(b).includes(p)) { relier(p, a); relier(p, b) }
  }
  return { ids, aretes }
}

// 0.24 : mise en page de tout l'arbre, partagée par l'arbre complet (à plat) et « Tout l'arbre » de la Vie 3D.
// Rend { ids, gen, X, W, H } : génération de chaque personne (0 = `c`, négatif = plus ancien) et abscisse.
// Chaque rangée est faite de « foyers » (une personne et ses conjoints de la même génération, côte à côte). L'ordre des
// foyers suit la moyenne de leurs parents puis de leurs enfants (va-et-vient) ; leur place est la plus proche possible
// de cette moyenne sans jamais se toucher (régression isotone). La famille de sang de `c` tire plus fort que la
// belle-famille. Plusieurs ordres de départ sont essayés ; on garde l'arbre le plus serré aux traits les plus courts.
export function miseEnPage(fam, c) {
  const W = 128, H = 110, ECART = 16
  const gen = new Map([[c, 0]]), file = [c]
  while (file.length) {
    const x = file.shift()
    for (const p of fam.parents(x)) if (!gen.has(p)) { gen.set(p, gen.get(x) - 1); file.push(p) }
    for (const e of fam.enfants(x)) if (!gen.has(e)) { gen.set(e, gen.get(x) + 1); file.push(e) }
    for (const k of [...fam.conjoints(x), ...fam.fratrie(x)]) if (!gen.has(k)) { gen.set(k, gen.get(x)); file.push(k) }
  }
  const ids = [...gen.keys()]
  const rangs = new Map()
  for (const x of ids) (rangs.get(gen.get(x)) || rangs.set(gen.get(x), []).get(gen.get(x))).push(x)
  const gs = [...rangs.keys()].sort((a, b) => a - b)

  // famille de sang de `c` : ses ancêtres et tous leurs descendants
  const sang = new Set(), anc = [c], ancetres = new Set([c])
  while (anc.length) { const x = anc.pop(); for (const p of fam.parents(x)) if (!ancetres.has(p)) { ancetres.add(p); anc.push(p) } }
  const pile = [...ancetres]
  while (pile.length) { const x = pile.pop(); if (sang.has(x)) continue; sang.add(x); pile.push(...fam.enfants(x)) }

  const largeur = (f) => f.membres.length * W
  function essai(racines) {
    const vu = new Set(), ordre = []
    const visiter = (x) => {
      if (vu.has(x)) return
      vu.add(x); ordre.push(x)
      for (const k of fam.conjoints(x)) if (!vu.has(k)) { vu.add(k); ordre.push(k) }
      for (const e of [...fam.enfants(x), ...fam.conjoints(x).flatMap((k) => fam.enfants(k))]) visiter(e)
    }
    racines.forEach(visiter); ids.forEach(visiter)
    const rang = new Map(ordre.map((x, i) => [x, i]))
    // foyers : composantes des couples dans une rangée, en chaîne (ex-conjoint, personne, conjoint)
    const foyers = new Map()
    for (const g of gs) {
      const pris = new Set(), liste = []
      for (const x of rangs.get(g).slice().sort((a, b) => rang.get(a) - rang.get(b))) {
        if (pris.has(x)) continue
        const groupe = [], p2 = [x]
        while (p2.length) { const y = p2.pop(); if (pris.has(y)) continue; pris.add(y); groupe.push(y)
          for (const k of fam.conjoints(y)) if (gen.get(k) === g && !pris.has(k)) p2.push(k) }
        const dans = (y) => fam.conjoints(y).filter((k) => groupe.includes(k))
        const bout = groupe.slice().sort((a, b) => dans(a).length - dans(b).length || rang.get(a) - rang.get(b))[0]
        const chaine = [bout], mis = new Set([bout])
        while (chaine.length < groupe.length) {
          const suite = dans(chaine[chaine.length - 1]).find((k) => !mis.has(k)) || groupe.find((k) => !mis.has(k))
          chaine.push(suite); mis.add(suite)
        }
        if (chaine.length === 2 && fam.P.get(chaine[1])?.genre === 'homme' && fam.P.get(chaine[0])?.genre !== 'homme') chaine.reverse()
        liste.push({ membres: chaine, x: 0 })
      }
      foyers.set(g, liste)
    }
    const X = new Map()
    const poser = (f) => f.membres.forEach((m, i) => X.set(m, f.x - largeur(f) / 2 + (i + 0.5) * W))
    const tasser = (liste, voulu) => {
      const dec = [], cible = []
      let cumul = 0
      liste.forEach((f, i) => { const d = cumul + largeur(f) / 2; dec.push(d); cible.push(voulu[i] - d); cumul += largeur(f) + ECART })
      const blocs = []
      for (const v of cible) {
        blocs.push({ s: v, n: 1 })
        while (blocs.length > 1 && blocs[blocs.length - 2].s / blocs[blocs.length - 2].n > blocs[blocs.length - 1].s / blocs[blocs.length - 1].n) {
          const b = blocs.pop(), a = blocs[blocs.length - 1]; a.s += b.s; a.n += b.n
        }
      }
      let i = 0
      for (const b of blocs) for (let k = 0; k < b.n; k++, i++) liste[i].x = b.s / b.n + dec[i]
      liste.forEach(poser)
    }
    for (const g of gs) { const l = foyers.get(g); tasser(l, l.map(() => 0)) }
    const moyenne = (f, voisins) => {
      let s = 0, n = 0
      for (const m of f.membres) for (const q of voisins(m)) if (X.has(q) && !f.membres.includes(q)) { const w = sang.has(m) ? 4 : 1; s += w * X.get(q); n += w }
      return n ? s / n : null
    }
    const cout = () => {
      let t = 0
      for (const e of ids) { const ps = fam.parents(e).filter((q) => X.has(q)); if (ps.length) t += Math.abs(ps.reduce((a, q) => a + X.get(q), 0) / ps.length - X.get(e)) }
      const xs = ids.map((x) => X.get(x))
      return t + 0.6 * (Math.max(...xs) - Math.min(...xs))
    }
    let meilleur = { t: Infinity, X: null }
    for (let passe = 0; passe < 30; passe++) {
      const descend = passe % 2 === 0
      for (const g of descend ? gs : [...gs].reverse()) {
        const l = foyers.get(g)
        const voulu = l.map((f) => moyenne(f, descend ? fam.parents : fam.enfants)
          ?? (moyenne(f, fam.parents) === null && moyenne(f, fam.enfants) === null ? moyenne(f, fam.fratrie) : null) ?? f.x)
        const idx = l.map((_, i) => i).sort((a, b) => voulu[a] - voulu[b] || l[a].x - l[b].x)
        const triee = idx.map((i) => l[i])
        foyers.set(g, triee)
        tasser(triee, idx.map((i) => voulu[i]))
      }
      if (!descend) { const t = cout(); if (t < meilleur.t - 1) meilleur = { t, X: new Map(X) } }
    }
    return meilleur
  }

  const sansParents = ids.filter((x) => !fam.parents(x).length)
  const parAge = sansParents.slice().sort((a, b) => gen.get(a) - gen.get(b))
  const essais = [
    parAge,
    parAge.slice().reverse(),
    [...parAge.filter((x) => ancetres.has(x)), ...parAge.filter((x) => !ancetres.has(x))],
    [...parAge.filter((x) => !ancetres.has(x)), ...parAge.filter((x) => ancetres.has(x))],
  ]
  let mieux = null
  for (const r of essais) { const m = essai(r); if (!mieux || m.t < mieux.t) mieux = m }
  // couloirs vides de haut en bas (deux parties de l'arbre sans lien entre elles) : ramenés à une carte de large
  const X = mieux.X, tries = ids.slice().sort((a, b) => X.get(a) - X.get(b))
  let decal = 0, bord = -Infinity
  for (const x of tries) {
    const g = X.get(x) - W / 2
    if (bord > -Infinity && g - bord > W) decal += g - bord - W
    bord = Math.max(bord, X.get(x) + W / 2)
    X.set(x, X.get(x) - decal)
  }
  return { ids, gen, X, W, H }
}
