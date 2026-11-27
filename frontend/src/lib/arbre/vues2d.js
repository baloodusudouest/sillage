// 0.23 : les trois vues à plat de l'arbre (SVG) : éventail, sablier, arbre complet. Prototypes validés par Julien le
// 27/11/2026. Glisser pour se déplacer, pincer (ou molette) pour zoomer, toucher une personne : `surChoix(id)`.
// `surligne` ({ ids, aretes }) : le chemin entre deux personnes brille, le reste s'estompe.
import { annees, initiales, masquee, prenomNom, teinte } from './famille.js'

const NS = 'http://www.w3.org/2000/svg'

export function creerVues2D(svg, fam, { surChoix = () => {} } = {}) {
  const monde = document.createElementNS(NS, 'g')
  const defs = document.createElementNS(NS, 'defs')
  svg.append(defs, monde)
  let vb = { x: 0, y: 0, w: 100, h: 100 }, n = 0, surligne = null, dessines = new Set()

  const el = (nom, at = {}, parent = monde) => { const e = document.createElementNS(NS, nom); for (const k in at) e.setAttribute(k, at[k]); parent.appendChild(e); return e }
  const txt = (x, y, t, at = {}, parent = monde) => { const e = el('text', { x, y, 'text-anchor': 'middle', 'dominant-baseline': 'middle', fill: '#f2ece2', 'font-size': 12, ...at }, parent); e.textContent = t; return e }
  const eteint = (id) => surligne && !surligne.ids.has(id)
  const brille = (a, b) => surligne && surligne.aretes.has(a + '|' + b)

  function visage(g, x, y, r, p, centre) {
    const mort = !!p.decede, lum = surligne?.ids.has(p.id)
    el('circle', { cx: x, cy: y, r: r + (centre || lum ? 4 : 2), fill: 'none', stroke: lum ? '#e9dcff' : centre ? '#a98fd8' : mort ? 'rgba(201,209,220,.35)' : 'rgba(169,143,216,.6)', 'stroke-width': centre || lum ? 3 : 1.5 }, g)
    el('circle', { cx: x, cy: y, r, fill: masquee(p) ? '#24212c' : mort ? '#3a3742' : `hsl(${teinte(p.nom || p.id)} 30% 38%)` }, g)
    txt(x, y + 1, initiales(p), { 'font-size': r * 0.75, 'font-weight': 600, fill: mort ? '#c9c4d2' : '#f2ece2' }, g)
    if (p.visage) {
      const id = 'c' + (n++)
      const clip = el('clipPath', { id }, defs); el('circle', { cx: x, cy: y, r }, clip)
      el('image', { href: p.visage, x: x - r, y: y - r, width: 2 * r, height: 2 * r, 'clip-path': `url(#${id})`, preserveAspectRatio: 'xMidYMid slice',
                    style: mort ? 'filter:grayscale(1) brightness(.75)' : '' }, g)
    }
  }
  function carte(x, y, id, { w = 128, centre = false } = {}) {
    const p = fam.P.get(id); if (!p) return
    dessines.add(id)
    const g = el('g', { class: 'personne', 'data-id': id, transform: `translate(${x},${y})`, opacity: eteint(id) ? 0.22 : 1, role: 'button', 'aria-label': p.nom || 'Personne' })
    const lum = surligne?.ids.has(id)
    el('rect', { x: -w / 2, y: -27, width: w, height: 54, rx: 12, fill: centre ? '#2a2145' : '#18142a',
                 stroke: lum ? '#e9dcff' : centre ? '#a98fd8' : p.decede ? 'rgba(201,209,220,.18)' : 'rgba(169,143,216,.45)', 'stroke-width': centre || lum ? 2 : 1 }, g)
    visage(g, -w / 2 + 22, 0, 14, p, centre)
    const [pr, no] = prenomNom(p), tx = -w / 2 + 44
    txt(tx, no ? -11 : -4, pr, { 'text-anchor': 'start', 'font-size': 13, 'font-weight': 600 }, g)
    if (no) txt(tx, 4, no, { 'text-anchor': 'start', 'font-size': 10.5, fill: '#cfc7dd' }, g)
    if (annees(p)) txt(tx, no ? 17 : 11, annees(p), { 'text-anchor': 'start', 'font-size': 10, fill: p.decede ? '#8f879e' : '#a49cb8' }, g)
  }
  const ligne = (d, { couleur = 'rgba(169,143,216,.55)', tirets = false, lum = false, faible = false } = {}) =>
    el('path', { d, fill: 'none', stroke: lum ? '#e9dcff' : couleur, 'stroke-width': lum ? 3 : 1.6, 'stroke-dasharray': tirets ? '5 5' : 'none', opacity: faible ? 0.25 : 1 })

  // ---------------------------------------------------------------- éventail
  function eventail(c) {
    const r0 = 46, w = 46, G = 4
    const cases = [[c]]
    for (let g = 1; g <= G; g++) cases.push(cases[g - 1].flatMap((x) => (x ? fam.pereMere(x) : [null, null])))
    const arc = (r1, r2, a1, a2) => {
      const p = (r, a) => [Math.cos(a) * r, Math.sin(a) * r]
      const [x1, y1] = p(r2, a1), [x2, y2] = p(r2, a2), [x3, y3] = p(r1, a2), [x4, y4] = p(r1, a1)
      return `M${x1},${y1} A${r2},${r2} 0 0 1 ${x2},${y2} L${x3},${y3} A${r1},${r1} 0 0 0 ${x4},${y4} Z`
    }
    for (let g = 1; g <= G; g++) {
      const nb = 2 ** g, r1 = r0 + (g - 1) * w + 2, r2 = r0 + g * w
      cases[g].forEach((id, k) => {
        const a1 = Math.PI + (k / nb) * Math.PI, a2 = Math.PI + ((k + 1) / nb) * Math.PI, cote = k < nb / 2
        const p = id ? fam.P.get(id) : null
        if (id) dessines.add(id)
        const lum = id && surligne?.ids.has(id)
        const g_ = el('g', id ? { class: 'personne', 'data-id': id, opacity: eteint(id) ? 0.25 : 1, role: 'button', 'aria-label': p.nom || 'Personne' } : {})
        el('path', { d: arc(r1, r2, a1 + 0.004, a2 - 0.004), stroke: lum ? '#e9dcff' : '#0b0910', 'stroke-width': lum ? 2.5 : 1.5,
                     fill: !id ? 'rgba(255,255,255,.03)' : p.decede ? (cote ? '#2b2440' : '#262a33') : cote ? '#3b2f5c' : '#2f3a45' }, g_)
        if (!id) return
        const am = (a1 + a2) / 2, rm = (r1 + r2) / 2, x = Math.cos(am) * rm, y = Math.sin(am) * rm, deg = am * 180 / Math.PI
        const [pr, no] = prenomNom(p)
        if (g <= 2) {
          const t = el('g', { transform: `translate(${x},${y})` }, g_)
          txt(0, -8, pr, { 'font-size': g === 1 ? 13 : 11.5, 'font-weight': 600 }, t)
          if (no) txt(0, 6, no, { 'font-size': 9.5, fill: '#cfc7dd' }, t)
          txt(0, 18, annees(p), { 'font-size': 9, fill: '#a49cb8' }, t)
        } else {
          const t = el('g', { transform: `translate(${x},${y}) rotate(${deg - 180}) ${deg < 270 ? 'rotate(180)' : ''}` }, g_)
          txt(0, -5, pr, { 'font-size': g === 3 ? 10 : 8.5, 'font-weight': 600 }, t)
          txt(0, 7, (p.naissance || '').slice(0, 4), { 'font-size': 8, fill: '#a49cb8' }, t)
        }
      })
    }
    const P0 = fam.P.get(c)
    dessines.add(c)
    const gc = el('g', { class: 'personne', 'data-id': c, role: 'button', 'aria-label': P0.nom || 'Personne' })
    el('path', { d: arc(0, r0, Math.PI, 2 * Math.PI), fill: '#2a2145', stroke: '#a98fd8', 'stroke-width': 2 }, gc)
    visage(gc, 0, -25, 12, P0, true)
    txt(0, -6, prenomNom(P0)[0], { 'font-size': 10.5, 'font-weight': 600 }, gc)
    let y = 40
    const rangee = (titre, ids) => {
      if (!ids.length) return
      txt(0, y, titre, { 'font-size': 11, fill: '#a49cb8' }); y += 38
      const w_ = 132, tot = ids.length * w_ - 8
      ids.forEach((id, i) => carte(-tot / 2 + w_ / 2 + i * w_ - 4, y, id)); y += 46
    }
    rangee('Conjoint·e', fam.conjoints(c))
    rangee('Frères et sœurs', fam.fratrie(c))
    rangee('Enfants', fam.enfants(c))
    rangee('Petits-enfants', fam.enfants(c).flatMap((e) => fam.enfants(e)))
    return { x: -230, y: -(r0 + G * w) - 10, w: 460, h: r0 + G * w + y + 20 }
  }

  // ---------------------------------------------------------------- sablier
  function sablier(c) {
    const W = 136, H = 84, G = 3
    const niv = [[c]]
    for (let g = 1; g <= G; g++) niv.push(niv[g - 1].flatMap((x) => (x ? fam.pereMere(x) : [null, null])))
    const largeur = 2 ** G * W, pos = new Map()
    for (let g = 1; g <= G; g++) niv[g].forEach((id, k) => { if (id) pos.set(id, [-largeur / 2 + (k + 0.5) * (largeur / 2 ** g), -g * H]) })
    for (let g = 0; g < G; g++) niv[g].forEach((id, k) => {
      if (!id) return
      const x = g === 0 ? 0 : pos.get(id)[0], y = -g * H, ps = [niv[g + 1][2 * k], niv[g + 1][2 * k + 1]].filter(Boolean)
      if (!ps.length) return
      const ym = y - H / 2, xs = ps.map((q) => pos.get(q)[0])
      const lum = ps.some((q) => brille(id, q))
      ligne(`M${x},${y - 27} V${ym} M${Math.min(...xs, x)},${ym} H${Math.max(...xs, x)}`, { lum, faible: surligne && !lum })
      for (const q of ps) ligne(`M${pos.get(q)[0]},${ym} V${pos.get(q)[1] + 27}`, { lum: brille(id, q), faible: surligne && !brille(id, q) })
    })
    for (const [id, [x, y]] of pos) carte(x, y, id, { w: W - 12 })
    const fr = fam.fratrie(c), cj = fam.conjoints(c)
    fr.forEach((id, i) => { const x = -(i + 1) * W - 20; ligne(`M${x},-27 V${-H / 2}`, { couleur: 'rgba(169,143,216,.35)', lum: brille(c, id) }); carte(x, 0, id, { w: W - 12 }) })
    if (fr.length) ligne(`M${-fr.length * W - 20},${-H / 2} H0`, { couleur: 'rgba(169,143,216,.35)', lum: fr.some((id) => brille(c, id)) })
    carte(0, 0, c, { w: W - 12, centre: true })
    cj.forEach((id, i) => { const x = (i + 1) * W; ligne(`M${x - W + (W - 12) / 2},0 H${x - (W - 12) / 2}`, { couleur: '#c9d1dc', tirets: fam.ex(c, id), lum: brille(c, id) }); carte(x, 0, id, { w: W - 12 }) })
    const ens = fam.enfants(c), tot = ens.length * W, mx = cj.length ? W / 2 : 0
    if (ens.length) ligne(`M${mx},0 V${H / 2} M${-tot / 2 + W / 2 + mx},${H / 2} H${tot / 2 - W / 2 + mx}`, { lum: ens.some((e) => brille(c, e)) })
    ens.forEach((id, i) => {
      const x = -tot / 2 + W / 2 + i * W + mx
      ligne(`M${x},${H / 2} V${H - 27}`, { lum: brille(c, id) }); carte(x, H, id, { w: W - 12 })
      const pe = fam.enfants(id)
      pe.forEach((q, j) => { const xx = x + (j - (pe.length - 1) / 2) * W; ligne(`M${x},${H + 27} V${H * 1.5} H${xx} V${2 * H - 27}`, { lum: brille(id, q) }); carte(xx, 2 * H, q, { w: W - 12 }) })
    })
    const gauche = Math.min(-largeur / 2, -fr.length * W - 20 - W / 2), droite = Math.max(largeur / 2, (cj.length + 0.5) * W)
    return { x: gauche - 10, y: -G * H - 40, w: droite - gauche + 20, h: (G + 2) * H + 60, telephone: { w: 600, y: -H } }
  }

  // ---------------------------------------------------------------- arbre complet
  function complet(c) {
    const gen = new Map([[c, 0]]), f = [c]
    while (f.length) {
      const x = f.shift()
      for (const p of fam.parents(x)) if (!gen.has(p)) { gen.set(p, gen.get(x) - 1); f.push(p) }
      for (const e of fam.enfants(x)) if (!gen.has(e)) { gen.set(e, gen.get(x) + 1); f.push(e) }
      for (const k of [...fam.conjoints(x), ...fam.fratrie(x)]) if (!gen.has(k)) { gen.set(k, gen.get(x)); f.push(k) }
    }
    const ids = [...gen.keys()], W = 140, H = 110, rangs = new Map()
    for (const x of ids) (rangs.get(gen.get(x)) || rangs.set(gen.get(x), []).get(gen.get(x))).push(x)
    const gs = [...rangs.keys()].sort((a, b) => a - b)
    const vu = new Set(), ordre = []
    const visiter = (x) => {
      if (vu.has(x)) return
      vu.add(x); ordre.push(x)
      for (const k of fam.conjoints(x)) if (!vu.has(k)) { vu.add(k); ordre.push(k) }
      for (const e of [...fam.enfants(x), ...fam.conjoints(x).flatMap((k) => fam.enfants(k))]) visiter(e)
    }
    ids.filter((x) => !fam.parents(x).length).sort((a, b) => gen.get(a) - gen.get(b)).forEach(visiter)
    ids.forEach(visiter)
    const rang = new Map(ordre.map((x, i) => [x, i]))
    const X = new Map()
    const rangee = (g) => rangs.get(g).sort((a, b) => (X.has(a) && X.has(b) ? X.get(a) - X.get(b) : rang.get(a) - rang.get(b)))
    for (const g of gs) rangee(g).forEach((x, i) => X.set(x, i * W))
    for (let passe = 0; passe < 12; passe++) {
      const descend = passe % 2 === 0
      for (const g of descend ? gs : [...gs].reverse()) {
        const r = rangee(g)
        const voulu = r.map((x) => {
          const ref = (descend ? fam.parents(x) : fam.enfants(x)).filter((q) => X.has(q))
          return ref.length ? ref.reduce((s, q) => s + X.get(q), 0) / ref.length : X.get(x)
        })
        r.forEach((x, i) => X.set(x, voulu[i]))
        r.sort((a, b) => X.get(a) - X.get(b))
        for (let i = 1; i < r.length; i++) if (X.get(r[i]) - X.get(r[i - 1]) < W) X.set(r[i], X.get(r[i - 1]) + W)
        const moy = r.reduce((s, x, i) => s + X.get(x) - voulu[i], 0) / r.length
        r.forEach((x) => X.set(x, X.get(x) - moy * 0.5))
      }
    }
    const Y = (x) => gen.get(x) * H, vus = new Set()
    for (const a of ids) for (const b of fam.conjoints(a)) {
      if (vus.has(b + '|' + a) || !X.has(b)) continue
      vus.add(a + '|' + b)
      ligne(`M${Math.min(X.get(a), X.get(b)) + (W - 16) / 2},${Y(a)} H${Math.max(X.get(a), X.get(b)) - (W - 16) / 2}`, { couleur: '#c9d1dc', tirets: fam.ex(a, b), lum: brille(a, b), faible: surligne && !brille(a, b) })
    }
    for (const e of ids) {
      const ps = fam.parents(e).filter((p) => X.has(p)); if (!ps.length) continue
      const mx = ps.reduce((s, p) => s + X.get(p), 0) / ps.length, ym = Y(e) - H / 2, lum = ps.some((p) => brille(p, e))
      ligne(`M${mx},${Y(ps[0]) + (ps.length > 1 ? 0 : 27)} V${ym} H${X.get(e)} V${Y(e) - 27}`, { lum, faible: surligne && !lum })
    }
    for (const x of ids) carte(X.get(x), Y(x), x, { w: W - 16, centre: x === c })
    const xs = ids.map((x) => X.get(x)), ys = ids.map(Y)
    const sur = surligne ? ids.filter((x) => surligne.ids.has(x)) : []
    const boite = sur.length > 1 ? (() => { const a = sur.map((x) => X.get(x)), b = sur.map(Y)
      return { x: Math.min(...a) - W, y: Math.min(...b) - H * 0.8, w: Math.max(...a) - Math.min(...a) + 2 * W, h: Math.max(...b) - Math.min(...b) + 1.6 * H } })() : null
    return { x: Math.min(...xs) - W, y: Math.min(...ys) - H, w: Math.max(...xs) - Math.min(...xs) + 2 * W, h: Math.max(...ys) - Math.min(...ys) + 2 * H,
             foyer: [X.get(c), Y(c)], boite }
  }

  // ---------------------------------------------------------------- chemin entre deux personnes (0.23.1)
  // Schéma de parenté : on remonte de la personne au centre jusqu'à l'ancêtre commun (colonne de gauche), puis on
  // redescend jusqu'à la personne cherchée (colonne de droite) ; un frère, une sœur ou un conjoint décale d'une colonne.
  function cheminVue(c, ch, lienDe) {
    const W = 170, H = 96, pos = []
    let x = 0, y = 0, monte = false
    ch.etapes.forEach((e, i) => {
      if (i) {
        if (e.rel === 'parent') { if (!monte && pos.length > 1 && !['parent', 'conjoint', null].includes(ch.etapes[i - 1].rel)) x += 1; y -= 1; monte = true }
        else if (e.rel === 'enfant') { if (monte) { x += 1; monte = false } y += 1 }
        else { x += 1; monte = false }
      }
      pos.push([x * W, y * H])
    })
    for (let i = 1; i < pos.length; i++) {
      const [x0, y0] = pos[i - 1], [x1, y1] = pos[i], rel = ch.etapes[i].rel
      if (rel === 'conjoint') ligne(`M${x0 + (W - 22) / 2},${y0} H${x1 - (W - 22) / 2}`, { lum: true, tirets: fam.ex(ch.etapes[i - 1].id, ch.etapes[i].id) })
      else if (rel === 'frere') ligne(`M${x0},${y0 - 27} V${y0 - H / 2} H${x1} V${y1 - 27}`, { lum: true })
      else { const [hx, hy, bx, by] = y1 < y0 ? [x1, y1, x0, y0] : [x0, y0, x1, y1]; ligne(`M${hx},${hy + 27} V${(hy + by) / 2} H${bx} V${by - 27}`, { lum: true }) }
    }
    ch.etapes.forEach((e, i) => {
      carte(pos[i][0], pos[i][1], e.id, { w: W - 22, centre: i === 0 })
      const mot = i ? lienDe(e.id) : ''
      if (mot) txt(pos[i][0], pos[i][1] + 40, mot, { 'font-size': 11, fill: '#b9a3e6', 'font-weight': 600, stroke: '#0b0a10', 'stroke-width': 5, 'paint-order': 'stroke' })
    })
    const xs = pos.map((p) => p[0]), ys = pos.map((p) => p[1])
    return { x: Math.min(...xs) - W / 2 - 20, y: Math.min(...ys) - 60, w: Math.max(...xs) - Math.min(...xs) + W + 40, h: Math.max(...ys) - Math.min(...ys) + 140 }
  }

  // ---------------------------------------------------------------- cadrage, déplacement, toucher
  const appliquer = () => svg.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`)
  function cadrer(c, vue) {
    const r = svg.getBoundingClientRect(), W = r.width || 1, H = r.height || 1, rapport = W / H
    let { x, y, w, h } = c
    if (c.boite) {                                      // 0.23.1 : tout le chemin à l'écran, entre la barre du haut et l'encart du résultat
      const b = c.boite, haut = 150, bas = W < 700 ? H * 0.4 : 190, He = Math.max(120, H - haut - bas)
      const s = Math.min((W * 0.92) / b.w, He / b.h, 1.25)                // pixels par unité, sans grossir à outrance
      vb = { x: b.x + b.w / 2 - W / s / 2, y: b.y + b.h / 2 - (haut + He / 2) / s, w: W / s, h: H / s }
      appliquer()
      return
    }
    if (vue === 'complet') { w = Math.max(700, Math.min(w, 900)); h = w / rapport; x = c.foyer[0] - w / 2; y = c.foyer[1] - h / 2 }
    else if (c.telephone && W < 700) { w = c.telephone.w; h = w / rapport; x = -w / 2 + 40; y = c.telephone.y - h / 2 + 60 }
    else if (w / h > rapport) { const nh = w / rapport; y -= (nh - h) / 2; h = nh } else { const nw = h * rapport; x -= (nw - w) / 2; w = nw }
    const haut = 150 * (h / H)                          // place pour la barre du haut
    vb = { x, y: y - haut, w, h: h + haut }
    appliquer()
  }
  const VUES = { eventail, sablier, complet }
  function dessiner(vue, centre, chemin = null, garderCadre = false, extra = {}) {
    surligne = chemin
    dessines = new Set()
    monde.replaceChildren(); defs.replaceChildren()
    const c = vue === 'chemin' ? cheminVue(centre, extra.ch, extra.lienDe) : VUES[vue](centre)
    if (vue === 'chemin') c.boite = { x: c.x, y: c.y, w: c.w, h: c.h }
    if (!garderCadre) cadrer(c, vue)
    return dessines
  }

  const doigts = new Map(); let depart = null, bouge = false
  const surBas = (e) => { svg.setPointerCapture?.(e.pointerId); doigts.set(e.pointerId, [e.clientX, e.clientY]); depart = { vb: { ...vb }, doigts: new Map(doigts), cible: e.target.closest?.('.personne') }; bouge = false }
  const surBouge = (e) => {
    if (!doigts.has(e.pointerId) || !depart) return
    doigts.set(e.pointerId, [e.clientX, e.clientY])
    const r = svg.getBoundingClientRect()
    if (doigts.size === 1 && depart.doigts.size === 1) {
      const [x0, y0] = [...depart.doigts.values()][0], [x1, y1] = [...doigts.values()][0]
      if (Math.hypot(x1 - x0, y1 - y0) > 6) bouge = true
      vb.x = depart.vb.x - (x1 - x0) * (depart.vb.w / r.width); vb.y = depart.vb.y - (y1 - y0) * (depart.vb.w / r.width); appliquer()
    } else if (doigts.size === 2) {
      bouge = true
      const [a0, b0] = [...depart.doigts.values()], [a1, b1] = [...doigts.values()]
      if (!a0 || !b0) { depart = { vb: { ...vb }, doigts: new Map(doigts) }; return }
      const s = Math.hypot(a0[0] - b0[0], a0[1] - b0[1]) / Math.max(1, Math.hypot(a1[0] - b1[0], a1[1] - b1[1]))
      const mx = (a0[0] + b0[0]) / 2, my = (a0[1] + b0[1]) / 2
      const wx = depart.vb.x + (mx - r.left) / r.width * depart.vb.w, wy = depart.vb.y + (my - r.top) / r.height * depart.vb.h
      vb.w = Math.min(6000, Math.max(120, depart.vb.w * s)); vb.h = vb.w * (depart.vb.h / depart.vb.w)
      vb.x = wx - (mx - r.left) / r.width * vb.w; vb.y = wy - (my - r.top) / r.height * vb.h; appliquer()
    }
  }
  const surHaut = (e) => {
    if (!bouge && depart?.cible && doigts.size === 1) surChoix(depart.cible.dataset.id)
    doigts.delete(e.pointerId); depart = { vb: { ...vb }, doigts: new Map(doigts) }
  }
  const surAnnule = (e) => doigts.delete(e.pointerId)
  const surMolette = (e) => {
    e.preventDefault()
    const r = svg.getBoundingClientRect(), wx = vb.x + (e.clientX - r.left) / r.width * vb.w, wy = vb.y + (e.clientY - r.top) / r.height * vb.h
    const s = Math.exp(e.deltaY * 0.0015), nw = Math.min(6000, Math.max(120, vb.w * s)), k = nw / vb.w
    vb.x = wx - (wx - vb.x) * k; vb.y = wy - (wy - vb.y) * k; vb.w = nw; vb.h *= k; appliquer()
  }
  svg.addEventListener('pointerdown', surBas); svg.addEventListener('pointermove', surBouge)
  svg.addEventListener('pointerup', surHaut); svg.addEventListener('pointercancel', surAnnule)
  svg.addEventListener('wheel', surMolette, { passive: false })
  return {
    dessiner,
    detruire() {
      svg.removeEventListener('pointerdown', surBas); svg.removeEventListener('pointermove', surBouge)
      svg.removeEventListener('pointerup', surHaut); svg.removeEventListener('pointercancel', surAnnule)
      svg.removeEventListener('wheel', surMolette)
      monde.remove(); defs.remove()
    },
  }
}
