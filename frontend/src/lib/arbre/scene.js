// 0.22 : la scène 3D de l'arbre (constellation et hélice), chargée seulement à l'ouverture de l'arbre.
// Une seule scène : un InstancedMesh pour tous les visages (un appel de dessin), des segments pour les liens,
// un ciel étoilé. Deux dispositions calculées une fois ; la bascule les fait glisser de l'une à l'autre.
// Visages : atlas de vignettes (128 px, 64 px au-delà de 1 024 personnes), rempli au fil du chargement.
// Loin de la caméra, un visage devient un point lumineux. Prototype mesuré sur iPhone le 27/11/2026 : 60 i/s à 400.
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const LAVANDE = new THREE.Color('#a98fd8')
const ARGENT = new THREE.Color('#c9d1dc')
const FOND = 0x0b0910

function hasard(graine) { let s = graine >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296) }
function teinte(texte) { let h = 0; for (const c of texte || '?') h = (h * 31 + c.charCodeAt(0)) >>> 0; return h % 360 }
function initiales(nom) {
  const m = (nom || '').trim().split(/\s+/).filter(Boolean)
  return ((m[0]?.[0] || '') + (m.length > 1 ? m.at(-1)[0] : '')).toUpperCase()
}

// ---------------------------------------------------------------- dispositions

function constellation(P, L, index) {
  const n = P.length, r = hasard(9), pos = new Float32Array(n * 3), v = new Float32Array(n * 3)
  const gmax = Math.max(0, ...P.map((p) => p.generation))
  const hauteur = (p) => (gmax / 2 - p.generation) * 4
  P.forEach((p, i) => { pos[i * 3] = (r() - 0.5) * 40; pos[i * 3 + 1] = hauteur(p) + (r() - 0.5) * 6; pos[i * 3 + 2] = (r() - 0.5) * 40 })
  const paires = L.map((l) => [index.get(l.de), index.get(l.vers), l.type === 'parent' ? 3.2 : 1.6]).filter(([a, b]) => a != null && b != null)
  const tours = n > 600 ? 140 : 220
  for (let t = 0; t < tours; t++) {
    const k = 1 - t / tours
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      let dx = pos[i * 3] - pos[j * 3], dy = pos[i * 3 + 1] - pos[j * 3 + 1], dz = pos[i * 3 + 2] - pos[j * 3 + 2]
      const d2 = dx * dx + dy * dy + dz * dz + 0.01
      if (d2 > 400) continue
      const f = 2.6 / d2; dx *= f; dy *= f; dz *= f
      v[i * 3] += dx; v[i * 3 + 1] += dy; v[i * 3 + 2] += dz; v[j * 3] -= dx; v[j * 3 + 1] -= dy; v[j * 3 + 2] -= dz
    }
    for (const [a, b, repos] of paires) {
      const dx = pos[b * 3] - pos[a * 3], dy = pos[b * 3 + 1] - pos[a * 3 + 1], dz = pos[b * 3 + 2] - pos[a * 3 + 2]
      const d = Math.sqrt(dx * dx + dy * dy + dz * dz) + 1e-4, f = (d - repos) * 0.09 / d
      v[a * 3] += dx * f; v[a * 3 + 1] += dy * f; v[a * 3 + 2] += dz * f; v[b * 3] -= dx * f; v[b * 3 + 1] -= dy * f; v[b * 3 + 2] -= dz * f
    }
    for (let i = 0; i < n; i++) {
      v[i * 3 + 1] += (hauteur(P[i]) - pos[i * 3 + 1]) * 0.02          // les générations restent à peu près en couches
      for (let c = 0; c < 3; c++) { pos[i * 3 + c] += Math.max(-2, Math.min(2, v[i * 3 + c])) * k; v[i * 3 + c] *= 0.5 }
    }
  }
  return pos
}

function ordreFamilial(P, L, index) {
  // Parcours en profondeur depuis les plus anciens : une famille reste groupée sur son anneau
  const enfants = new Map(), conjoints = new Map()
  for (const l of L) {
    const a = index.get(l.de), b = index.get(l.vers)
    if (a == null || b == null) continue
    if (l.type === 'parent') (enfants.get(a) || enfants.set(a, []).get(a)).push(b)
    else if (l.type === 'conjoint') {
      (conjoints.get(a) || conjoints.set(a, []).get(a)).push(b);
      (conjoints.get(b) || conjoints.set(b, []).get(b)).push(a)
    }
  }
  const vu = new Set(), ordre = []
  const visiter = (i) => {
    if (vu.has(i)) return
    vu.add(i); ordre.push(i)
    for (const c of conjoints.get(i) || []) if (!vu.has(c)) { vu.add(c); ordre.push(c) }
    for (const e of enfants.get(i) || []) visiter(e)
    for (const c of conjoints.get(i) || []) for (const e of enfants.get(c) || []) visiter(e)
  }
  P.map((_, i) => i).sort((a, b) => P[a].generation - P[b].generation).forEach(visiter)
  return ordre
}

function helice(P, L, index) {
  const pos = new Float32Array(P.length * 3), parGen = new Map()
  for (const i of ordreFamilial(P, L, index)) (parGen.get(P[i].generation) || parGen.set(P[i].generation, []).get(P[i].generation)).push(i)
  const gmax = Math.max(0, ...P.map((p) => p.generation))
  const anneaux = []
  for (const [g, ids] of parGen) {
    const R = Math.max(5, ids.length * 1.45 / (2 * Math.PI)), y = (gmax / 2 - g) * 5.2      // ancêtres en haut
    ids.forEach((i, k) => {
      const a = (k / ids.length) * Math.PI * 2 + g * 0.55
      pos[i * 3] = Math.cos(a) * R; pos[i * 3 + 1] = y; pos[i * 3 + 2] = Math.sin(a) * R
    })
    anneaux.push({ g, R, y })
  }
  return { pos, anneaux, gmax }
}

// ---------------------------------------------------------------- vignettes

function atlas(P, maxTex) {
  const cote = Math.min(4096, maxTex)
  let cell = 128
  if (Math.ceil(P.length / Math.floor(cote / cell)) * cell > cote) cell = 64
  const cols = Math.floor(cote / cell), rows = Math.max(1, Math.ceil(P.length / cols))
  const toile = document.createElement('canvas')
  toile.width = cols * cell; toile.height = rows * cell
  const x = toile.getContext('2d')
  const peindre = (i, p) => {
    const ox = (i % cols) * cell, oy = Math.floor(i / cols) * cell, s = cell, h = teinte(p.nom || p.id)
    const gr = x.createRadialGradient(ox + s * 0.5, oy + s * 0.35, s * 0.05, ox + s * 0.5, oy + s * 0.5, s * 0.62)
    gr.addColorStop(0, `hsl(${h} 30% 46%)`); gr.addColorStop(1, `hsl(${(h + 40) % 360} 25% 18%)`)
    x.fillStyle = gr; x.fillRect(ox, oy, s, s)
    x.fillStyle = 'rgba(242,236,226,.92)'
    x.font = `600 ${Math.round(s * 0.3)}px Inter, system-ui, sans-serif`
    x.textAlign = 'center'; x.textBaseline = 'middle'
    x.fillText(initiales(p.nom) || '·', ox + s * 0.5, oy + s * 0.53)
  }
  P.forEach((p, i) => peindre(i, p))
  const tex = new THREE.CanvasTexture(toile)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.minFilter = THREE.LinearMipmapLinearFilter
  tex.anisotropy = 4
  const poser = (i, image) => {
    const ox = (i % cols) * cell, oy = Math.floor(i / cols) * cell
    const c = Math.min(image.naturalWidth || image.width, image.naturalHeight || image.height)
    const sx = ((image.naturalWidth || image.width) - c) / 2, sy = ((image.naturalHeight || image.height) - c) / 2
    x.drawImage(image, sx, sy, c, c, ox, oy, cell, cell)
  }
  return { tex, cols, rows, cell, w: toile.width, h: toile.height, poser }
}

function chargerVisages(P, A, fini) {
  // Six à la fois ; la texture est rafraîchie au plus quatre fois par seconde
  const file = P.map((p, i) => [p.visage, i]).filter(([u]) => u)
  let actifs = 0, sale = false, arret = false
  const minuterie = setInterval(() => { if (sale) { A.tex.needsUpdate = true; sale = false } }, 250)
  const suivant = () => {
    if (arret) return
    while (actifs < 6 && file.length) {
      const [url, i] = file.shift()
      actifs++
      const img = new Image()
      img.decoding = 'async'
      img.onload = () => { if (!arret) { A.poser(i, img); sale = true }; actifs--; suivant() }
      img.onerror = () => { actifs--; suivant() }
      img.src = url
    }
    if (!actifs && !file.length) { clearInterval(minuterie); if (sale) A.tex.needsUpdate = true; fini?.() }
  }
  suivant()
  return () => { arret = true; clearInterval(minuterie) }
}

// ---------------------------------------------------------------- scène

export function webglPossible() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')) } catch { return false }
}

export function creerScene(conteneur, donnees, { vue = 'constellation', surChoix = () => {} } = {}) {
  const reduit = matchMedia('(prefers-reduced-motion: reduce)').matches
  const P = donnees.personnes, L = donnees.liens
  const index = new Map(P.map((p, i) => [p.id, i]))
  const depart = index.get(donnees.depart) ?? 0
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
  const dpr = Math.min(devicePixelRatio || 1, 2)
  renderer.setPixelRatio(dpr)
  renderer.setClearColor(FOND, 1)
  conteneur.appendChild(renderer.domElement)
  renderer.domElement.style.touchAction = 'none'
  const gl = renderer.getContext()
  const maxTex = gl.getParameter(gl.MAX_TEXTURE_SIZE)

  const scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(FOND, 0.008)
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 900)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true; controls.dampingFactor = 0.08; controls.minDistance = 4; controls.maxDistance = 320
  const monde = new THREE.Group(); scene.add(monde)
  const jetables = []

  // Ciel étoilé
  const etoiles = (() => {
    const n = 2200, g = new THREE.BufferGeometry(), p = new Float32Array(n * 3), ph = new Float32Array(n), r = hasard(3)
    for (let i = 0; i < n; i++) {
      const u = r() * 2 - 1, a = r() * Math.PI * 2, R = 200 + r() * 260, s = Math.sqrt(1 - u * u)
      p[i * 3] = Math.cos(a) * s * R; p[i * 3 + 1] = u * R; p[i * 3 + 2] = Math.sin(a) * s * R; ph[i] = r() * 6.28
    }
    g.setAttribute('position', new THREE.BufferAttribute(p, 3)); g.setAttribute('ph', new THREE.BufferAttribute(ph, 1))
    const m = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { t: { value: 0 } },
      vertexShader: 'attribute float ph; uniform float t; varying float a; void main(){ a = .45 + .55*sin(t*1.3+ph); vec4 mv = modelViewMatrix*vec4(position,1.); gl_PointSize = 2.2*(300./-mv.z); gl_Position = projectionMatrix*mv; }',
      fragmentShader: 'varying float a; void main(){ float d = length(gl_PointCoord-.5); if(d>.5) discard; gl_FragColor = vec4(vec3(.82,.78,1.)*(1.-d*2.)*a, 1.); }',
    })
    const pts = new THREE.Points(g, m); scene.add(pts); jetables.push(g, m)
    return m
  })()

  const posA = { constellation: constellation(P, L, index), helice: null }
  const H = helice(P, L, index)
  posA.helice = H.pos
  const posCour = new Float32Array(posA[vue] || posA.constellation)
  const A = atlas(P, maxTex)
  const arreterVisages = chargerVisages(P, A)

  // Visages : un seul InstancedMesh
  const plan = new THREE.PlaneGeometry(1, 1)
  const geo = new THREE.InstancedBufferGeometry()
  geo.index = plan.index
  geo.setAttribute('position', plan.getAttribute('position'))
  geo.setAttribute('uv', plan.getAttribute('uv'))
  geo.instanceCount = P.length
  const off = new THREE.InstancedBufferAttribute(posCour, 3); off.setUsage(THREE.DynamicDrawUsage)
  const cellUV = new Float32Array(P.length * 2), drap = new Float32Array(P.length * 4)
  P.forEach((p, i) => {
    cellUV[i * 2] = (i % A.cols) * A.cell / A.w
    cellUV[i * 2 + 1] = 1 - (Math.floor(i / A.cols) + 1) * A.cell / A.h
    drap[i * 4] = p.decede ? 1 : 0
    drap[i * 4 + 1] = i === depart || p.invite ? 1 : 0
    drap[i * 4 + 2] = (i * 2.399) % 6.28
    drap[i * 4 + 3] = p.statut === 'masque' ? 1 : 0
  })
  geo.setAttribute('offset', off)
  geo.setAttribute('cellUV', new THREE.InstancedBufferAttribute(cellUV, 2))
  geo.setAttribute('drap', new THREE.InstancedBufferAttribute(drap, 4))
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: {
      atlas: { value: A.tex }, cellSize: { value: new THREE.Vector2(A.cell / A.w, A.cell / A.h) },
      carte: { value: vue === 'helice' ? 1 : 0 }, t: { value: 0 }, haut: { value: 800 }, sel: { value: -1 },
      lav: { value: LAVANDE }, arg: { value: ARGENT },
    },
    vertexShader: `
      attribute vec3 offset; attribute vec2 cellUV; attribute vec4 drap;
      uniform float carte, t, haut, sel; varying vec2 vUv, vCell; varying float vMort, vFocus, vLoin, vScint;
      void main(){
        vUv = uv; vCell = cellUV; vMort = drap.x; vFocus = max(drap.y, float(gl_InstanceID)==sel ? 1. : 0.);
        vScint = .5 + .5*sin(t*1.7 + drap.z);
        vec4 mv = modelViewMatrix * vec4(offset, 1.);
        float s = mix(1.7, 1.6, carte) * (1. + .35*vFocus) * mix(1., .55, drap.w);
        float px = s * projectionMatrix[1][1] * haut * .5 / -mv.z;
        vLoin = max(1. - smoothstep(4., 10., px), drap.w);
        mv.xy += position.xy * 1.4 * s * vec2(mix(1., .78, carte), 1.);
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `
      uniform sampler2D atlas; uniform vec2 cellSize; uniform float carte; uniform vec3 lav, arg;
      varying vec2 vUv, vCell; varying float vMort, vFocus, vLoin, vScint;
      float boite(vec2 p, vec2 b, float r){ vec2 q = abs(p)-b+r; return length(max(q,0.))+min(max(q.x,q.y),0.)-r; }
      void main(){
        vec2 p = (vUv - .5) * 1.4;
        float d = mix(length(p) - .36, boite(p, vec2(.46, .48), .08), carte);
        vec3 face = texture2D(atlas, vCell + clamp(p + .5, .01, .99) * cellSize).rgb;
        if (vMort > .5) face = vec3(dot(face, vec3(.299,.587,.114))) * .62;
        vec3 halo = mix(lav, arg, vMort);
        float a = 1. - smoothstep(-.005, .01, d);
        float bord = (1. - smoothstep(0., .02, abs(d + .012))) * mix(.55, 1., vFocus);
        float glow = exp(-max(d, 0.) * mix(16., 7., vFocus)) * mix(.35, .95, vFocus) * (.7 + .3*vScint);
        vec3 c = mix(face, halo, bord*.8);
        vec4 corps = vec4(c, a) + vec4(halo * glow, glow * (1.-a));
        float r = length(p) / 1.4;
        float etoile = exp(-r*r*40.) * (.6 + .4*vScint) + exp(-r*9.)*.25;
        gl_FragColor = mix(corps, vec4(halo * etoile * 1.4, etoile), vLoin);
        if (gl_FragColor.a < .01) discard;
      }`,
  })
  const mesh = new THREE.Mesh(geo, mat); mesh.frustumCulled = false; mesh.renderOrder = 2; monde.add(mesh)
  jetables.push(plan, geo, mat, A.tex)

  // Liens : parent/enfant lavande, couple argent, fratrie lavande pâle ; ex-couple en pointillé
  const PALE = LAVANDE.clone().multiplyScalar(0.6)
  const segments = (garder, couleur) => {
    const ls = L.filter(garder).filter((l) => index.has(l.de) && index.has(l.vers))
    const g = new THREE.BufferGeometry(), p = new Float32Array(ls.length * 6), c = new Float32Array(ls.length * 6)
    ls.forEach((l, i) => { const col = couleur(l); for (const k of [0, 3]) { c[i * 6 + k] = col.r; c[i * 6 + k + 1] = col.g; c[i * 6 + k + 2] = col.b } })
    g.setAttribute('position', new THREE.BufferAttribute(p, 3).setUsage(THREE.DynamicDrawUsage))
    g.setAttribute('color', new THREE.BufferAttribute(c, 3))
    g.userData.liens = ls
    jetables.push(g)
    return g
  }
  const lignes = new THREE.LineSegments(
    segments((l) => !l.divorce, (l) => (l.type === 'conjoint' ? ARGENT : l.type === 'fratrie' ? PALE : LAVANDE)),
    new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false }))
  const lignesEx = new THREE.LineSegments(segments((l) => !!l.divorce, () => ARGENT),
    new THREE.LineDashedMaterial({ color: ARGENT, dashSize: 0.35, gapSize: 0.35, transparent: true, opacity: 0.5, depthWrite: false }))
  monde.add(lignes, lignesEx)
  jetables.push(lignes.material, lignesEx.material)

  // Axe de l'hélice (deux brins, lavande et argent) et un anneau par génération
  const axe = new THREE.Group(), anneaux = new THREE.Group()
  const hautAxe = (H.gmax / 2 + 1.2) * 5.2
  for (const [col, ph] of [[LAVANDE, 0], [ARGENT, Math.PI]]) {
    const pts = []
    for (let i = 0; i <= 240; i++) { const y = -hautAxe + (i / 240) * hautAxe * 2, a = y * 0.55 + ph; pts.push(new THREE.Vector3(Math.cos(a) * 1.4, y, Math.sin(a) * 1.4)) }
    const courbe = new THREE.CatmullRomCurve3(pts)
    for (const [rayon, op] of [[0.09, 0.9], [0.35, 0.12]]) {
      const g = new THREE.TubeGeometry(courbe, 400, rayon, 8), m = new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false })
      axe.add(new THREE.Mesh(g, m)); jetables.push(g, m)
    }
  }
  const genDepart = P[depart]?.generation
  for (const { g: gen, R, y } of H.anneaux) {
    const pts = []
    for (let i = 0; i <= 128; i++) { const a = i / 128 * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(a) * R, y - 1.15, Math.sin(a) * R)) }
    const g = new THREE.BufferGeometry().setFromPoints(pts)
    const m = new THREE.LineBasicMaterial({ color: gen === genDepart ? LAVANDE : ARGENT, transparent: true, opacity: gen === genDepart ? 0.55 : 0.18, depthWrite: false })
    anneaux.add(new THREE.Line(g, m)); jetables.push(g, m)
  }
  monde.add(axe, anneaux)
  const regler = (grp, a) => { grp.traverse((o) => { if (o.material) { o.material.userData.o0 ??= o.material.opacity; o.material.opacity = o.material.userData.o0 * a } }); grp.visible = a > 0.01 }
  regler(axe, vue === 'helice' ? 1 : 0); regler(anneaux, vue === 'helice' ? 1 : 0)

  function majPositions() {
    for (const ls of [lignes, lignesEx]) {
      const p = ls.geometry.getAttribute('position').array
      ls.geometry.userData.liens.forEach((l, i) => {
        const a = index.get(l.de), b = index.get(l.vers)
        for (let k = 0; k < 3; k++) { p[i * 6 + k] = posCour[a * 3 + k]; p[i * 6 + 3 + k] = posCour[b * 3 + k] }
      })
      ls.geometry.getAttribute('position').needsUpdate = true
      ls.geometry.computeBoundingSphere()
    }
    lignesEx.computeLineDistances()
    off.needsUpdate = true
  }
  majPositions()

  // Cadrage et vol de caméra
  let vol = null, trans = null, choisi = -1, mode = vue
  const rayon = (pos) => { let m = 0; for (let i = 0; i < pos.length; i += 3) m = Math.max(m, Math.hypot(pos[i], pos[i + 1], pos[i + 2])); return m }
  function cadrer(v, anime = true) {
    const portrait = conteneur.clientWidth < conteneur.clientHeight
    const d = rayon(posA[v]) * (v === 'helice' ? (portrait ? 2.6 : 1.9) : (portrait ? 1.9 : 1.25)) + 6
    const cv = new THREE.Vector3(0, v === 'helice' ? d * 0.28 : d * 0.12, d)
    if (!anime || reduit) { camera.position.copy(cv); controls.target.set(0, 0, 0); return }
    vol = { t0: performance.now(), de: controls.target.clone(), vers: new THREE.Vector3(), cd: camera.position.clone(), cv }
  }
  function viser(i) {
    monde.updateMatrixWorld()
    const cible = new THREE.Vector3(posCour[i * 3], posCour[i * 3 + 1], posCour[i * 3 + 2]).applyMatrix4(monde.matrixWorld)
    const cv = cible.clone().add(camera.position.clone().sub(controls.target).setLength(16))
    if (reduit) { controls.target.copy(cible); camera.position.copy(cv); return }
    vol = { t0: performance.now(), de: controls.target.clone(), vers: cible, cd: camera.position.clone(), cv }
  }
  function choisir(i, prevenir = true) {
    choisi = i
    mat.uniforms.sel.value = i
    if (i >= 0) viser(i)
    if (prevenir) surChoix(i >= 0 ? P[i] : null)
  }

  // Taille
  function redimensionner() {
    const w = conteneur.clientWidth || 1, h = conteneur.clientHeight || 1
    renderer.setSize(w, h, false)
    renderer.domElement.style.width = '100%'; renderer.domElement.style.height = '100%'
    camera.aspect = w / h; camera.updateProjectionMatrix()
    mat.uniforms.haut.value = h * renderer.getPixelRatio()
  }
  const observateur = new ResizeObserver(redimensionner)
  observateur.observe(conteneur)
  redimensionner()
  cadrer(mode, false)

  // Toucher : la personne la plus proche du doigt, à l'écran
  let bas = null, repos = performance.now()
  const surBas = (e) => { bas = { x: e.clientX, y: e.clientY }; repos = performance.now() }
  const surHaut = (e) => {
    if (!bas || Math.hypot(e.clientX - bas.x, e.clientY - bas.y) > 8) return
    const r = renderer.domElement.getBoundingClientRect(), v = new THREE.Vector3()
    let meilleur = -1, bd = 28 * 28
    monde.updateMatrixWorld()
    for (let i = 0; i < P.length; i++) {
      v.set(posCour[i * 3], posCour[i * 3 + 1], posCour[i * 3 + 2]).applyMatrix4(monde.matrixWorld).project(camera)
      if (v.z > 1) continue
      const x = (v.x + 1) / 2 * r.width + r.left, y = (1 - v.y) / 2 * r.height + r.top
      const d = (x - e.clientX) ** 2 + (y - e.clientY) ** 2
      if (d < bd) { bd = d; meilleur = i }
    }
    choisir(meilleur)
  }
  renderer.domElement.addEventListener('pointerdown', surBas)
  renderer.domElement.addEventListener('pointerup', surHaut)
  const surPerte = (e) => { e.preventDefault(); surChoix(null, 'perdu') }
  renderer.domElement.addEventListener('webglcontextlost', surPerte)

  // Boucle
  let derniere = performance.now(), anim = 0, actif = true
  function boucle(now) {
    if (!actif) return
    const dt = Math.min(100, now - derniere); derniere = now
    const t = now / 1000
    mat.uniforms.t.value = t; etoiles.uniforms.t.value = t
    lignes.material.opacity = (reduit ? 0.5 : 0.45 + 0.12 * Math.sin(t * 1.1))
    if (trans) {
      const k = Math.min(1, (now - trans.t0) / trans.dur), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2
      for (let i = 0; i < posCour.length; i++) posCour[i] = trans.de[i] + (trans.vers[i] - trans.de[i]) * e
      const h = trans.cible === 'helice' ? e : 1 - e
      mat.uniforms.carte.value = h; regler(axe, h); regler(anneaux, h)
      majPositions()
      if (k >= 1) trans = null
    }
    if (vol) {
      const k = Math.min(1, (now - vol.t0) / 900), e = 1 - Math.pow(1 - k, 3)
      controls.target.lerpVectors(vol.de, vol.vers, e); camera.position.lerpVectors(vol.cd, vol.cv, e)
      if (k >= 1) vol = null
    }
    if (!reduit && choisi < 0 && now - repos > 5000) monde.rotation.y += dt * 0.00006
    controls.update()
    renderer.render(scene, camera)
    anim = requestAnimationFrame(boucle)
  }
  anim = requestAnimationFrame(boucle)
  const surVisibilite = () => {
    if (document.hidden) { actif = false; cancelAnimationFrame(anim) } else if (!actif) { actif = true; derniere = performance.now(); anim = requestAnimationFrame(boucle) }
  }
  document.addEventListener('visibilitychange', surVisibilite)

  return {
    basculer(vers) {
      if (vers === mode || !posA[vers]) return
      trans = { de: new Float32Array(posCour), vers: posA[vers], t0: performance.now(), dur: reduit ? 1 : 1600, cible: vers }
      mode = vers
      choisir(-1, false)
      cadrer(vers)
    },
    choisir: (id) => { const i = index.get(id); if (i != null) choisir(i) },
    relacher: () => choisir(-1, false),
    recadrer: () => cadrer(mode),
    detruire() {
      actif = false
      cancelAnimationFrame(anim)
      arreterVisages()
      observateur.disconnect()
      document.removeEventListener('visibilitychange', surVisibilite)
      renderer.domElement.removeEventListener('pointerdown', surBas)
      renderer.domElement.removeEventListener('pointerup', surHaut)
      renderer.domElement.removeEventListener('webglcontextlost', surPerte)
      controls.dispose()
      for (const j of jetables) j.dispose?.()
      renderer.dispose()
      renderer.domElement.remove()
    },
  }
}
