// 0.23 : l'arbre de vie en 3D (prototype validé par Julien le 27/11/2026), chargé à l'ouverture de cette vue.
// Le sens se lit sans réfléchir, même en tournant : un étage par génération à hauteur fixe et nommé (« ↑ Parents »,
// « ↓ Enfants »…), rotation autour de l'axe vertical seulement (l'arbre ne se renverse jamais), sève lumineuse qui
// descend des parents vers les enfants, lien écrit sur chaque carte. Toucher une carte : `surChoix(id)`.
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { annees, initiales, masquee, miseEnPage, prenomNom, teinte } from './famille.js'

const LAV = new THREE.Color('#a98fd8'), ARG = new THREE.Color('#c9d1dc'), BLANC = new THREE.Color('#e9dcff'), FOND = 0x0b0910
const ETAGE = 6
const RAYONS = [0, 4.5, 9, 13.5]
const ETAGES = { 3: '↑ Arrière-grands-parents', 2: '↑ Grands-parents', 1: '↑ Parents', [-1]: '↓ Enfants', [-2]: '↓ Petits-enfants' }

export function webglPossible() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')) } catch { return false }
}

export function creerVie(conteneur, fam, { lienDe = () => '', surChoix = () => {} } = {}) {
  const reduit = matchMedia('(prefers-reduced-motion: reduce)').matches
  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2)); renderer.setClearColor(FOND, 1)
  conteneur.appendChild(renderer.domElement)
  renderer.domElement.style.touchAction = 'none'
  const scene = new THREE.Scene(); scene.fog = new THREE.Fog(FOND, 70, 190)
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 500)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true; controls.minDistance = 8; controls.maxDistance = 140
  controls.minPolarAngle = 1.15; controls.maxPolarAngle = 1.9            // l'arbre ne se renverse jamais
  const monde = new THREE.Group(); scene.add(monde)
  let deco = new THREE.Group(); monde.add(deco)
  const sprites = new Map(), images = new Map(), jetables = []
  let disposition = null, depuis = new Map(), t0 = 0, temps = 0, cible = null, surligne = null

  // Ciel étoilé
  {
    const n = 1800, g = new THREE.BufferGeometry(), p = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) { const u = Math.random() * 2 - 1, a = Math.random() * 6.28, R = 120 + Math.random() * 150, s = Math.sqrt(1 - u * u); p.set([Math.cos(a) * s * R, u * R, Math.sin(a) * s * R], i * 3) }
    g.setAttribute('position', new THREE.BufferAttribute(p, 3))
    const m = new THREE.PointsMaterial({ color: 0xcfc7ff, size: 0.7, transparent: true, opacity: 0.7 })
    scene.add(new THREE.Points(g, m)); jetables.push(g, m)
  }

  const fil = (pts, couleur, op, tirets = false) => {
    const g = new THREE.BufferGeometry().setFromPoints(pts)
    const m = tirets ? new THREE.LineDashedMaterial({ color: couleur, transparent: true, opacity: op, dashSize: 0.4, gapSize: 0.35, depthWrite: false })
      : new THREE.LineBasicMaterial({ color: couleur, transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false })
    const l = new THREE.Line(g, m); if (tirets) l.computeLineDistances(); return l
  }

  // ---------------------------------------------------------------- cartes
  function peindre(id, centre) {
    const p = fam.P.get(id), lien = lienDe(id), lum = surligne?.ids.has(id)
    const W = 320, H = 132, cv = document.createElement('canvas'), x = cv.getContext('2d')
    cv.width = W; cv.height = H
    x.beginPath(); x.roundRect(4, 4, W - 8, H - 8, 22)
    x.fillStyle = centre ? 'rgba(48,36,82,.96)' : 'rgba(24,20,42,.92)'; x.fill()
    x.lineWidth = centre || lum ? 5 : 2.5
    x.strokeStyle = lum ? '#e9dcff' : centre ? '#a98fd8' : p.decede ? 'rgba(201,209,220,.35)' : 'rgba(169,143,216,.7)'; x.stroke()
    x.save(); x.beginPath(); x.arc(62, H / 2, 36, 0, Math.PI * 2); x.closePath()
    x.fillStyle = masquee(p) ? '#24212c' : p.decede ? '#3a3742' : `hsl(${teinte(p.nom || id)} 32% 40%)`; x.fill()
    const img = images.get(id)
    if (img?.complete && img.naturalWidth) {
      x.clip()
      if (p.decede) x.filter = 'grayscale(1) brightness(.8)'
      const c = Math.min(img.naturalWidth, img.naturalHeight)
      x.drawImage(img, (img.naturalWidth - c) / 2, (img.naturalHeight - c) / 2, c, c, 26, H / 2 - 36, 72, 72)
      x.filter = 'none'
    } else {
      x.fillStyle = '#f2ece2'; x.font = '600 28px Inter, system-ui, sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'
      x.fillText(initiales(p), 62, H / 2 + 1)
    }
    x.restore()
    x.beginPath(); x.arc(62, H / 2, 36, 0, Math.PI * 2); x.lineWidth = 3; x.strokeStyle = p.decede ? 'rgba(201,209,220,.5)' : 'rgba(169,143,216,.9)'; x.stroke()
    const [pr, no] = prenomNom(p)
    x.textAlign = 'left'; x.textBaseline = 'middle'
    x.font = '700 32px Inter, system-ui, sans-serif'; x.fillStyle = '#f2ece2'; x.fillText(pr, 112, lien ? 34 : 42, W - 124)
    x.font = '500 21px Inter, system-ui, sans-serif'; x.fillStyle = '#cfc7dd'; x.fillText([no, annees(p)].filter(Boolean).join(' · '), 112, lien ? 68 : 84, W - 124)
    if (lien) { x.font = '600 20px Inter, system-ui, sans-serif'; x.fillStyle = '#b9a3e6'; x.fillText(lien, 112, 100, W - 124) }
    const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4
    return t
  }
  function carte(id, centre) {
    let s = sprites.get(id)
    const map = peindre(id, centre)
    if (!s) { s = new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, depthWrite: false })); s.userData.id = id; s.renderOrder = 3; monde.add(s); sprites.set(id, s) }
    else { s.material.map?.dispose(); s.material.map = map; s.material.needsUpdate = true }
    const k = centre ? 1.25 : 1
    s.scale.set(4.6 * k, 1.9 * k, 1)
    s.material.opacity = surligne && !surligne.ids.has(id) ? 0.22 : 1
    const p = fam.P.get(id)
    if (p.visage && !images.has(id)) {
      const img = new Image(); img.decoding = 'async'
      img.onload = () => { const sp = sprites.get(id); if (sp) { sp.material.map?.dispose(); sp.material.map = peindre(id, sp.userData.centre); sp.material.needsUpdate = true } }
      img.src = p.visage; images.set(id, img)
    }
    s.userData.centre = centre
    return s
  }
  function etiquetteEtage(texte, y) {
    const cv = document.createElement('canvas'), x = cv.getContext('2d'); cv.width = 512; cv.height = 72
    x.font = '600 34px Inter, system-ui, sans-serif'; x.fillStyle = 'rgba(201,209,220,.85)'; x.textBaseline = 'middle'; x.fillText(texte, 8, 38, 496)
    const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false }))
    sp.scale.set(7.1, 1, 1); sp.position.set(0, y + 2.1, 0); sp.renderOrder = 1
    return sp
  }

  // ---------------------------------------------------------------- disposition autour de la personne au centre
  // 0.24 : « Tout l'arbre » (oncles, cousins, belle-famille…) : la mise en page de l'arbre complet enroulée sur un
  // cylindre, un étage par génération ; la personne au centre face à l'écran.
  function disposerTout(c) {
    const { ids, gen, X, W } = miseEnPage(fam, c)
    const ECH = 5.6 / W, pos = new Map(), liens = [], branches = [], etages = new Set(), rayons = new Map()
    const xs = ids.map((x) => X.get(x)), L = (Math.max(...xs) - Math.min(...xs) + W * 2) * ECH
    const R = Math.max(7, L / (2 * Math.PI)), x0 = X.get(c)
    for (const id of ids) {
      const g = -gen.get(id), a = Math.PI / 2 - ((X.get(id) - x0) * ECH) / R
      pos.set(id, new THREE.Vector3(Math.cos(a) * R, g * ETAGE, Math.sin(a) * R)); etages.add(g); rayons.set(g, R)
    }
    const vus = new Set()
    for (const id of ids) {
      for (const e of fam.enfants(id)) if (pos.has(e)) branches.push([pos.get(id), pos.get(e), Math.abs(gen.get(e)), id, e, true])
      for (const k of fam.conjoints(id)) if (pos.has(k) && !vus.has(k + '|' + id)) { vus.add(id + '|' + k); liens.push([id, k, fam.ex(id, k) ? 'ex' : 'couple']) }
    }
    return { pos, liens, branches, etages, rayons }
  }

  function disposer(c) {
    const pos = new Map([[c, new THREE.Vector3(0, 0, 0)]]), liens = [], branches = [], etages = new Set([0])
    const pousser = (id, origine, azimut, g, ecart) => {
      if (!id || g > 3) return
      const ps = fam.pereMere(id).filter(Boolean)
      ps.forEach((p, i) => {
        if (pos.has(p)) return
        const az = azimut + (ps.length > 1 ? (i ? 1 : -1) * ecart : 0)
        const fin = new THREE.Vector3(Math.cos(az) * RAYONS[g], g * ETAGE, Math.sin(az) * RAYONS[g])
        pos.set(p, fin); branches.push([origine, fin, g, id, p]); etages.add(g)
        pousser(p, fin, az, g + 1, ecart * 0.5)
      })
    }
    pousser(c, new THREE.Vector3(0, 0, 0), Math.PI / 2, 1, Math.PI / 2)
    fam.conjoints(c).forEach((id, i) => { if (pos.has(id)) return; const a = -0.55 - i * 0.5; pos.set(id, new THREE.Vector3(Math.cos(a) * 7, 0, Math.sin(a) * 7)); liens.push([c, id, fam.ex(c, id) ? 'ex' : 'couple']) })
    fam.fratrie(c).forEach((id, i) => { if (pos.has(id)) return; const a = Math.PI + 0.55 + i * 0.45; pos.set(id, new THREE.Vector3(Math.cos(a) * 7, 0, Math.sin(a) * 7)); liens.push([c, id, 'fratrie']) })
    fam.enfants(c).forEach((id, i, t) => {
      if (pos.has(id)) return
      const a = -Math.PI / 2 + (i - (t.length - 1) / 2) * 0.9, fin = new THREE.Vector3(Math.cos(a) * 5, -ETAGE, Math.sin(a) * 5)
      pos.set(id, fin); branches.push([new THREE.Vector3(0, 0, 0), fin, 1.4, c, id]); etages.add(-1)
      fam.enfants(id).forEach((q, j, u) => {
        if (pos.has(q)) return
        const b = a + (j - (u.length - 1) / 2) * 0.45, f2 = new THREE.Vector3(Math.cos(b) * 9, -2 * ETAGE, Math.sin(b) * 9)
        pos.set(q, f2); branches.push([fin, f2, 2, id, q]); etages.add(-2)
      })
    })
    return { pos, liens, branches, etages }
  }

  function decorer(c) {
    monde.remove(deco)
    deco.traverse((o) => { o.geometry?.dispose(); o.material?.map?.dispose(); o.material?.dispose?.() })
    deco = new THREE.Group(); monde.add(deco)
    const { branches, etages, liens } = disposition
    for (const g of etages) {
      const R = disposition.rayons?.get(g) ?? (g > 0 ? RAYONS[g] : g === 0 ? 7 : g === -1 ? 5 : 9)
      const pts = []; for (let i = 0; i <= 96; i++) { const a = i / 96 * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(a) * (R + 2.5), g * ETAGE - 1.25, Math.sin(a) * (R + 2.5))) }
      deco.add(fil(pts, g >= 0 ? ARG : LAV, g === 0 ? 0.3 : 0.14))
      const p = fam.P.get(c)
      deco.add(etiquetteEtage(g === 0 ? `Génération de ${masquee(p) ? 'cette personne' : prenomNom(p)[0]}` : ETAGES[g] || (g > 0 ? `↑ ${g} générations au-dessus` : `↓ ${-g} générations au-dessous`), g * ETAGE))
    }
    const seve = []
    for (const [a, b, g, x, y, droit] of branches) {
      const bas = a.y < b.y ? a : b, haut = a.y < b.y ? b : a
      const k = droit ? 0.5 : 0.3                        // sur le cylindre, la branche ne plonge pas vers l'axe
      const milieu = new THREE.Vector3((bas.x + haut.x) * k, (bas.y + haut.y) / 2, (bas.z + haut.z) * k)
      const courbe = new THREE.QuadraticBezierCurve3(haut, milieu, bas)
      const lum = surligne?.aretes.has(x + '|' + y)
      deco.add(new THREE.Mesh(new THREE.TubeGeometry(courbe, 24, lum ? 0.3 : droit ? 0.07 : Math.max(0.07, 0.34 - Math.abs(g) * 0.07), 8),
        new THREE.MeshBasicMaterial({ color: lum ? BLANC : LAV.clone().lerp(ARG, Math.min(1, Math.max(0, g) / 3)), transparent: true,
          opacity: surligne && !lum ? 0.12 : lum ? 0.95 : droit ? 0.35 : 0.5, blending: THREE.AdditiveBlending, depthWrite: false })))
      if (!surligne || lum) for (let k = 0; k < 3; k++) seve.push({ courbe, t: k / 3 })
    }
    for (const [a, b, sorte] of liens) {
      const lum = surligne?.aretes.has(a + '|' + b)
      const l = fil([disposition.pos.get(a), disposition.pos.get(b)], lum ? BLANC : sorte === 'fratrie' ? LAV : ARG, surligne && !lum ? 0.1 : lum ? 1 : 0.5, sorte === 'ex')
      l.userData.lien = [a, b]; deco.add(l)
    }
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(Math.max(1, seve.length) * 3), 3))
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xe9dcff, size: 0.42, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false }))
    pts.userData.seve = seve; deco.add(pts)
  }

  let centre = null, toutAvant = false, tourner = null
  // l'angle `vers` (à 2π près) le plus proche de `de`, pour tourner par le plus court
  const proche = (de, vers) => vers + Math.round((de - vers) / (2 * Math.PI)) * 2 * Math.PI
  function montrer(c, chemin = null, tout = false) {
    const nouveauCentre = c !== centre || tout !== toutAvant
    centre = c; surligne = chemin; toutAvant = tout
    disposition = tout ? disposerTout(c) : disposer(c)
    depuis = new Map([...sprites].map(([id, s]) => [id, s.position.clone()]))
    t0 = performance.now()
    for (const [id, s] of sprites) if (!disposition.pos.has(id)) { monde.remove(s); s.material.map?.dispose(); s.material.dispose(); sprites.delete(id) }
    for (const [id, p] of disposition.pos) { const s = carte(id, id === c); if (!depuis.has(id)) { s.position.copy(p).multiplyScalar(0.2); depuis.set(id, s.position.clone()) } }
    decorer(c)
    if (nouveauCentre) {
      const R = Math.max(...[...disposition.pos.values()].map((v) => v.length()), 8)
      const portrait = conteneur.clientWidth < conteneur.clientHeight
      const Rc = disposition.rayons ? Math.max(...disposition.rayons.values()) : 0
      cible = Rc
        ? { pos: new THREE.Vector3(0, 7, Rc + (portrait ? 46 : 30)), regard: new THREE.Vector3(0, 1, Rc * 0.45), t0: performance.now(), de: camera.position.clone(), deR: controls.target.clone() }
        : { pos: new THREE.Vector3(0, 9, R * (portrait ? 2.9 : 1.7) + 6), regard: new THREE.Vector3(0, 4, 0), t0: performance.now(), de: camera.position.clone(), deR: controls.target.clone() }
      monde.rotation.y = 0
    }
    // 0.26.2 : un chemin allumé est tourné face à l'écran (milieu de ses personnes), et ne tourne plus tout seul
    if (chemin && chemin.ids.size) {
      let x = 0, z = 0
      for (const id of chemin.ids) { const p = disposition.pos.get(id); if (p) { x += p.x; z += p.z } }
      if (x || z) tourner = { de: monde.rotation.y, vers: proche(monde.rotation.y, Math.atan2(z, x) - Math.PI / 2), t0: performance.now() }
    }
    return new Set(disposition.pos.keys())
  }

  function redim() { const w = conteneur.clientWidth || 1, h = conteneur.clientHeight || 1; renderer.setSize(w, h, false); renderer.domElement.style.width = '100%'; renderer.domElement.style.height = '100%'; camera.aspect = w / h; camera.updateProjectionMatrix() }
  const obs = new ResizeObserver(redim); obs.observe(conteneur); redim()
  camera.position.set(0, 9, 60)

  const ray = new THREE.Raycaster(), souris = new THREE.Vector2()
  let bas = null, repos = performance.now()
  const surBas = (e) => { bas = [e.clientX, e.clientY]; repos = performance.now() }
  const surHaut = (e) => {
    if (!bas || Math.hypot(e.clientX - bas[0], e.clientY - bas[1]) > 8) return
    const r = renderer.domElement.getBoundingClientRect()
    souris.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1)
    ray.setFromCamera(souris, camera)
    const t = ray.intersectObjects([...sprites.values()])[0]
    if (t) surChoix(t.object.userData.id)
  }
  const surPerte = (e) => { e.preventDefault(); surChoix(null, 'perdu') }
  renderer.domElement.addEventListener('pointerdown', surBas)
  renderer.domElement.addEventListener('pointerup', surHaut)
  renderer.domElement.addEventListener('webglcontextlost', surPerte)

  let derniere = performance.now(), anim = 0, actif = true
  function boucle(now) {
    if (!actif) return
    const dt = Math.min(100, now - derniere); derniere = now; temps += dt
    const k = Math.min(1, (now - t0) / (reduit ? 1 : 1100)), e = 1 - Math.pow(1 - k, 3)
    for (const [id, s] of sprites) { const fin = disposition.pos.get(id); if (fin) s.position.lerpVectors(depuis.get(id) || fin, fin, e) }
    deco.traverse((o) => {
      if (o.userData?.seve) {
        const p = o.geometry.getAttribute('position')
        o.userData.seve.forEach((s, i) => { if (!reduit) s.t = (s.t + dt * 0.00035) % 1; const v = s.courbe.getPoint(s.t); p.setXYZ(i, v.x, v.y, v.z) })
        p.needsUpdate = true
      } else if (o.userData?.lien) {
        const [a, b] = o.userData.lien, sa = sprites.get(a), sb = sprites.get(b)
        if (sa && sb && k < 1) { o.geometry.setFromPoints([sa.position, sb.position]); if (o.material.isLineDashedMaterial) o.computeLineDistances() }
      }
    })
    if (cible) { const c = Math.min(1, (now - cible.t0) / 1100), ec = 1 - Math.pow(1 - c, 3); camera.position.lerpVectors(cible.de, cible.pos, ec); controls.target.lerpVectors(cible.deR, cible.regard, ec); if (c >= 1) cible = null }
    if (tourner) {
      const k = Math.min(1, (now - tourner.t0) / 900), e = 1 - (1 - k) ** 3
      monde.rotation.y = tourner.de + (tourner.vers - tourner.de) * e
      if (k >= 1) tourner = null
    } else if (!reduit && !surligne && now - repos > 3000) monde.rotation.y += dt * 0.00008
    controls.update()
    renderer.render(scene, camera)
    anim = requestAnimationFrame(boucle)
  }
  anim = requestAnimationFrame(boucle)
  const surVisibilite = () => { if (document.hidden) { actif = false; cancelAnimationFrame(anim) } else if (!actif) { actif = true; derniere = performance.now(); anim = requestAnimationFrame(boucle) } }
  document.addEventListener('visibilitychange', surVisibilite)

  return {
    montrer,
    detruire() {
      actif = false; cancelAnimationFrame(anim); obs.disconnect()
      document.removeEventListener('visibilitychange', surVisibilite)
      renderer.domElement.removeEventListener('pointerdown', surBas)
      renderer.domElement.removeEventListener('pointerup', surHaut)
      renderer.domElement.removeEventListener('webglcontextlost', surPerte)
      controls.dispose()
      deco.traverse((o) => { o.geometry?.dispose(); o.material?.map?.dispose(); o.material?.dispose?.() })
      for (const s of sprites.values()) { s.material.map?.dispose(); s.material.dispose() }
      for (const j of jetables) j.dispose?.()
      renderer.dispose(); renderer.domElement.remove()
    },
  }
}
