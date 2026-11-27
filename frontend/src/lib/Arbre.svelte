<script>
  // 0.22 : l'arbre de famille en 3D, en plein écran, par-dessus le chemin. Deux vues (constellation, hélice), la dernière
  // gardée sur l'appareil. Toucher un visage : la caméra va vers lui et sa carte s'ouvre.
  // Propriétaire : « Voir son sillage », « Ouvrir dans carnet » (ou Treemich). Invité : « Proposer une correction »
  // (envoyée à carnet par Sillage ; rien n'est écrit tout de suite). La scène 3D (three.js) n'est chargée qu'ici.
  import { onMount, onDestroy, tick } from 'svelte'
  import Croix from '$lib/Croix.svelte'
  import { dateLongue } from '$lib/dates.js'
  import { indexer, parente } from '$lib/arbre/parente.js'

  let { arbre, invite = null, apercu = false, restantes = 0, onfermer } = $props()
  // invite : { jeton } pour un invité ; null pour le propriétaire

  const CLE_VUE = 'sillage-arbre-vue'
  const CLE_AIDE = 'sillage-arbre-aide'
  const lireStock = (k) => { try { return localStorage.getItem(k) } catch { return null } }
  const ecrireStock = (k, v) => { try { localStorage.setItem(k, v) } catch { /* navigation privée */ } }

  let boite = $state(null)
  let scene = null
  let vue = $state(lireStock(CLE_VUE) === 'helice' ? 'helice' : 'constellation')
  let choisie = $state(null)
  let aide = $state(lireStock(CLE_AIDE) !== 'vu')
  let pret = $state(false)
  let sans3d = $state(false)
  let perdu = $state(false)
  let centre = $state(arbre.depart)          // invités : la personne d'où se lisent les liens (légende)
  let formulaire = $state(null)              // invité : la proposition en cours
  let envoi = $state({ attente: false, message: '', erreur: '' })
  let reste = $state(restantes)
  let liste = $state(false)                  // la liste des personnes (accessible sans la 3D, et pour chercher)
  let cherche = $state('')

  const ix = $derived(indexer(arbre.personnes, arbre.liens))
  const parId = $derived(new Map(arbre.personnes.map((p) => [p.id, p])))
  const nomDe = (p) => (p?.statut === 'masque' ? 'Personne non montrée' : p?.nom || 'Sans nom')
  const titre = $derived(invite ? 'Votre arbre de famille' : `L'arbre de ${nomDe(parId.get(arbre.depart))}`)
  const lien = $derived(choisie ? parente(ix, centre, choisie.id) : '')
  const deCentre = $derived(nomDe(parId.get(centre)).split(' ')[0])

  // « 1985 » → « Né en 1985 » ; « 1985-03-14 » → « Née le 14 mars 1985 »
  function dates(p) {
    if (!p || p.statut === 'masque') return ''
    const e = p.genre === 'femme' ? 'e' : p.genre === 'homme' ? '' : '(e)'
    const n = p.naissance ? (p.naissance.length >= 10 ? `Né${e} le ${dateLongue(p.naissance.slice(0, 10))}` : `Né${e} en ${p.naissance.slice(0, 4)}`) : ''
    const d = p.deces === 'inconnue' ? `décédé${e}` : p.deces ? (p.deces.length >= 10 ? `décès le ${dateLongue(p.deces.slice(0, 10))}` : `décès en ${p.deces.slice(0, 4)}`) : ''
    return [n, d].filter(Boolean).join(' · ') || (p.statut === 'mineur' || p.statut === 'inconnu' ? '' : 'Dates inconnues')
  }

  const conjointsDe = (id) => [...(ix.conjoints.get(id) || [])].map((x) => parId.get(x)).filter(Boolean)

  function basculer(v) {
    if (v === vue) return
    vue = v
    choisie = null
    formulaire = null
    ecrireStock(CLE_VUE, v)
    scene?.basculer(v)
  }
  function fermerAide() { aide = false; ecrireStock(CLE_AIDE, 'vu') }
  function fermerCarte() { choisie = null; formulaire = null; scene?.relacher() }
  function recentrer(id) { centre = id; scene?.choisir(id) }
  function depuisListe(p) {
    if (matchMedia('(max-width: 640px)').matches) liste = false
    fermerAide()
    scene?.choisir(p.id)
    choisie = p
  }
  const trouves = $derived.by(() => {
    const t = cherche.trim().toLowerCase()
    return [...arbre.personnes].filter((p) => !t || nomDe(p).toLowerCase().includes(t))
      .sort((a, b) => a.generation - b.generation || nomDe(a).localeCompare(nomDe(b)))
  })

  function ouvrirFormulaire() {
    envoi = { attente: false, message: '', erreur: '' }
    formulaire = { type: 'date', champ: 'naissance', valeur: '', autre: '', lien: 'enfant', mot: '' }
  }
  async function proposer(ev) {
    ev.preventDefault()
    if (!choisie || !formulaire) return
    envoi = { attente: true, message: '', erreur: '' }
    const f = formulaire
    const corps = { personne: choisie.id, type: f.type, mot: f.mot.trim() }
    if (f.type === 'date') Object.assign(corps, { champ: f.champ, valeur: f.valeur.trim(), autre: f.champ === 'mariage' ? f.autre || undefined : undefined })
    if (f.type === 'nom') Object.assign(corps, { champ: f.champ, valeur: f.valeur.trim() })
    if (f.type === 'lien') Object.assign(corps, { lien: f.lien })
    if (f.type === 'personne') Object.assign(corps, { valeur: f.valeur.trim() })
    try {
      const r = await fetch(`/api/invite/${encodeURIComponent(invite.jeton)}/arbre/proposition`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) })
      const j = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(typeof j.detail === 'string' ? j.detail : 'Sillage ne répond pas pour l\'instant.')
      reste = j.propositions_restantes ?? reste
      envoi = { attente: false, message: j.message || 'Merci, c\'est transmis à Julien', erreur: '' }
      formulaire = null
    } catch (e) { envoi = { attente: false, message: '', erreur: e.message } }
  }

  // Liste de secours (sans WebGL) : les personnes par génération, du plus ancien au plus jeune
  const parGeneration = $derived.by(() => {
    const m = new Map()
    for (const p of arbre.personnes) (m.get(p.generation) || m.set(p.generation, []).get(p.generation)).push(p)
    return [...m.entries()].sort((a, b) => a[0] - b[0])
  })

  const surTouche = (ev) => {
    if (ev.key !== 'Escape') return
    if (formulaire) formulaire = null
    else if (choisie) fermerCarte()
    else onfermer?.()
  }

  onMount(async () => {
    document.documentElement.style.overflow = 'hidden'
    const module = await import('$lib/arbre/scene.js')
    if (!module.webglPossible()) { sans3d = true; return }
    await tick()
    const donnees = {
      depart: arbre.depart, liens: arbre.liens,
      personnes: arbre.personnes.map((p) => ({ ...p, visage: !p.visage ? null
        : invite ? `/api/invite/${encodeURIComponent(invite.jeton)}/arbre/vignette/${p.id}` : `/api/arbre/vignette/${p.visage}` })),
    }
    try {
      scene = module.creerScene(boite, donnees, {
        vue,
        surChoix: (p, quoi) => {
          if (quoi === 'perdu') { perdu = true; return }
          choisie = p ? parId.get(p.id) : null
          formulaire = null
          envoi = { attente: false, message: '', erreur: '' }
          if (p) fermerAide()
        },
      })
      pret = true
    } catch { sans3d = true }
  })
  onDestroy(() => { scene?.detruire(); document.documentElement.style.overflow = '' })
</script>

<svelte:window onkeydown={surTouche} />

<div class="arbre" role="dialog" aria-modal="true" aria-label={titre}>
  <div class="scene" bind:this={boite} aria-hidden="true"></div>

  <header class="haut">
    <div class="verre titre-arbre">
      <span class="etiquette">Arbre</span>
      <span class="nom">{titre}</span>
    </div>
    {#if !sans3d}
      <div class="verre bascule" role="group" aria-label="Vue de l'arbre">
        <button type="button" aria-pressed={vue === 'constellation'} onclick={() => basculer('constellation')}>Constellation</button>
        <button type="button" aria-pressed={vue === 'helice'} onclick={() => basculer('helice')}>Hélice</button>
      </div>
      <div class="verre bascule"><button type="button" aria-pressed={liste} onclick={() => (liste = !liste)}>Liste</button></div>
    {/if}
  </header>
  <Croix label="Fermer l'arbre" onclick={() => onfermer?.()} />

  {#if invite && arbre.invites?.length > 1 && !sans3d}
    <ul class="verre legende" aria-label="Lire les liens depuis">
      {#each arbre.invites as i}
        <li><button type="button" aria-pressed={centre === i.id} onclick={() => recentrer(i.id)}>{i.prenom || 'Invité'}</button></li>
      {/each}
      <li><button type="button" onclick={() => { centre = arbre.depart; fermerCarte(); scene?.recadrer() }}>Ensemble</button></li>
    </ul>
  {/if}

  {#if perdu}
    <p class="verre message" role="alert">L'affichage 3D s'est arrêté. Fermez l'arbre et rouvrez-le.</p>
  {:else if sans3d}
    <div class="secours">
      <p class="discret">Cet appareil n'affiche pas la 3D : voici l'arbre en liste, du plus ancien au plus jeune.</p>
      {#each parGeneration as [g, gens]}
        <section>
          <h2 class="etiquette">Génération {g + 1}</h2>
          <ul>
            {#each gens as p}<li><strong>{nomDe(p)}</strong>{#if parente(ix, centre, p.id)}<span class="discret"> · {parente(ix, centre, p.id)}</span>{/if}{#if dates(p)}<span class="discret"> · {dates(p)}</span>{/if}</li>{/each}
          </ul>
        </section>
      {/each}
    </div>
  {:else if !pret}
    <p class="verre message" role="status">Préparation de l'arbre…</p>
  {:else if aide}
    <div class="verre aide" role="note">
      <p><strong>Touchez un visage</strong> pour voir qui c'est.</p>
      <p class="discret">Glissez pour tourner, pincez pour zoomer.</p>
      <button type="button" class="plein" onclick={fermerAide}>Compris</button>
    </div>
  {/if}

  {#if liste && !sans3d}
    <nav class="verre panneau" aria-label="Personnes de l'arbre">
      <input type="search" bind:value={cherche} placeholder="Chercher un nom" aria-label="Chercher un nom" autocomplete="off" />
      <ul>
        {#each trouves as p (p.id)}
          <li><button type="button" aria-current={choisie?.id === p.id ? 'true' : undefined} onclick={() => depuisListe(p)}>
            <span>{nomDe(p)}</span><span class="discret">{parente(ix, centre, p.id)}</span></button></li>
        {/each}
      </ul>
    </nav>
  {/if}

  {#if choisie}
    <section class="verre carte" aria-label={nomDe(choisie)}>
      <button type="button" class="fermer" aria-label="Fermer la carte" onclick={fermerCarte}>×</button>
      {#if lien}<p class="lien">{lien}{choisie.id !== centre ? ` de ${deCentre}` : ''}</p>{/if}
      <h2 class="nom-carte">{nomDe(choisie)}</h2>
      {#if dates(choisie)}<p class="discret">{dates(choisie)}</p>{/if}

      {#if !invite}
        <div class="actions">
          {#if choisie.sillage}<a class="plein" href={'#/chemin/' + choisie.sillage} onclick={() => onfermer?.()}>Voir son sillage</a>{/if}
          {#if choisie.carnet_uid && arbre.carnet}
            <a class="contour" href={`${arbre.carnet}/#/contacts/${encodeURIComponent(choisie.carnet_uid)}`} target="_blank" rel="noopener">Ouvrir dans carnet</a>
          {:else if arbre.treemich}
            <a class="contour" href={arbre.treemich} target="_blank" rel="noopener">Ouvrir dans Treemich</a>
          {/if}
        </div>
        {#if choisie.masque_invites}<p class="discret petit">Jamais montrée aux invités (case cochée dans carnet).</p>{/if}
      {:else if envoi.message}
        <p class="merci" role="status">{envoi.message}</p>
      {:else if formulaire}
        <form class="formulaire" onsubmit={proposer}>
          <label>Ce qui ne va pas
            <select bind:value={formulaire.type}>
              <option value="date">Une date fausse ou manquante</option>
              <option value="nom">Le nom ou son orthographe</option>
              <option value="lien">Un lien faux ou manquant</option>
              <option value="personne">Une personne manquante</option>
            </select>
          </label>
          {#if formulaire.type === 'date'}
            <label>Quelle date
              <select bind:value={formulaire.champ}>
                <option value="naissance">Naissance</option>
                <option value="deces">Décès</option>
                {#if conjointsDe(choisie.id).length}<option value="mariage">Mariage</option>{/if}
              </select>
            </label>
            {#if formulaire.champ === 'mariage'}
              <label>Avec
                <select bind:value={formulaire.autre}>
                  {#each conjointsDe(choisie.id) as c}<option value={c.id}>{nomDe(c)}</option>{/each}
                </select>
              </label>
            {/if}
            <label>La bonne date <span class="discret">(année seule, ou AAAA-MM-JJ ; vide si elle est fausse)</span>
              <input bind:value={formulaire.valeur} inputmode="numeric" placeholder="1952 ou 1952-04-18" autocomplete="off" maxlength="10" />
            </label>
          {:else if formulaire.type === 'nom'}
            <label>Quoi
              <select bind:value={formulaire.champ}><option value="prenom">Le prénom</option><option value="nom">Le nom de famille</option></select>
            </label>
            <label>Comment il s'écrit <input bind:value={formulaire.valeur} autocomplete="off" maxlength="80" required /></label>
          {:else if formulaire.type === 'lien'}
            <label>Il manque (ou c'est faux)
              <select bind:value={formulaire.lien}>
                <option value="parent">un parent</option><option value="enfant">un enfant</option>
                <option value="conjoint">un conjoint</option><option value="frere_soeur">un frère ou une sœur</option>
                <option value="autre">autre chose</option>
              </select>
            </label>
          {:else}
            <label>Son prénom (et son nom si vous le savez) <input bind:value={formulaire.valeur} autocomplete="off" maxlength="80" /></label>
          {/if}
          <label>Un mot pour Julien <span class="discret">{formulaire.type === 'lien' || formulaire.type === 'personne' ? '' : '(facultatif)'}</span>
            <textarea bind:value={formulaire.mot} rows="2" maxlength="300"></textarea>
          </label>
          {#if envoi.erreur}<p class="erreur" role="alert">{envoi.erreur}</p>{/if}
          <div class="actions">
            <button type="submit" class="plein" disabled={envoi.attente}>{envoi.attente ? 'Envoi…' : 'Envoyer à Julien'}</button>
            <button type="button" class="contour" onclick={() => (formulaire = null)}>Annuler</button>
          </div>
        </form>
      {:else if apercu}
        <p class="discret petit">Aperçu : l'invité peut proposer une correction depuis cette carte.</p>
      {:else if reste > 0}
        <div class="actions"><button type="button" class="contour" onclick={ouvrirFormulaire}>Proposer une correction</button></div>
      {:else}
        <p class="discret petit">Julien a déjà beaucoup de propositions à regarder : merci !</p>
      {/if}
    </section>
  {/if}
</div>

<style>
  .arbre { position: fixed; inset: 0; z-index: 60; background: #0b0910; color: var(--foreground); }
  .scene { position: absolute; inset: 0; }
  .scene :global(canvas) { display: block; }
  .verre { background: rgb(24 20 38 / 0.82); border: 1px solid rgb(201 209 220 / 0.14); border-radius: 1rem;
           backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); box-shadow: 0 10px 40px rgb(0 0 0 / 0.45); }
  .haut { position: absolute; z-index: 61; top: calc(0.75rem + env(safe-area-inset-top, 0px)); left: max(0.75rem, env(safe-area-inset-left, 0px));
          right: calc(4.25rem + env(safe-area-inset-right, 0px)); display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; pointer-events: none; }
  .haut > * { pointer-events: auto; }
  .titre-arbre { display: grid; padding: 0.45rem 0.9rem; min-width: 0; max-width: 100%; }
  .titre-arbre .nom { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bascule, .legende { display: flex; gap: 0.25rem; padding: 0.25rem; }
  .bascule button, .legende button { min-height: 2.5rem; padding: 0 0.9rem; border-radius: 0.75rem; border: 0; background: transparent;
                                     color: var(--foreground); font: inherit; font-size: 0.9rem; cursor: pointer; }
  .bascule button[aria-pressed='true'], .legende button[aria-pressed='true'] { background: var(--app); color: var(--app-contraste); font-weight: 600; }
  .legende { position: absolute; z-index: 61; left: max(0.75rem, env(safe-area-inset-left, 0px)); bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
             list-style: none; margin: 0; flex-wrap: wrap; max-width: calc(100vw - 1.5rem); }
  .message, .aide { position: absolute; z-index: 61; left: 50%; top: 50%; transform: translate(-50%, -50%); padding: 1rem 1.2rem;
                    width: min(22rem, calc(100vw - 2rem)); text-align: center; }
  .aide p { margin: 0 0 0.5rem; }
  .carte { position: absolute; z-index: 62; right: max(0.75rem, env(safe-area-inset-right, 0px)); bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
           width: min(22rem, calc(100vw - 1.5rem)); max-height: calc(100dvh - 7rem); overflow-y: auto; padding: 1rem 1.1rem; }
  .fermer { position: absolute; top: 0.4rem; right: 0.5rem; width: 2.75rem; height: 2.75rem; border: 0; background: none;
            color: var(--muted-foreground); font-size: 1.4rem; cursor: pointer; }
  .lien { margin: 0; padding-right: 2.5rem; font-size: 0.75rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--app); }
  .nom-carte { margin: 0.2rem 0 0.15rem; padding-right: 2rem; font-size: 1.3rem; font-weight: 600; overflow-wrap: anywhere; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.9rem; }
  .plein, .contour { display: inline-flex; align-items: center; justify-content: center; min-height: 2.75rem; padding: 0 1rem;
                     border-radius: 0.75rem; font: inherit; font-size: 0.92rem; text-decoration: none; cursor: pointer; }
  .plein { background: var(--app); color: var(--app-contraste); border: 1px solid var(--app); font-weight: 600; }
  .plein:disabled { opacity: 0.6; }
  .contour { background: transparent; color: var(--foreground); border: 1px solid rgb(201 209 220 / 0.25); }
  .contour:hover { border-color: var(--app); }
  .discret { color: var(--muted-foreground); }
  .petit { font-size: 0.82rem; margin: 0.6rem 0 0; }
  .merci { margin: 0.8rem 0 0; color: var(--app); }
  .erreur { margin: 0; color: #f19a9a; font-size: 0.88rem; }
  .formulaire { display: grid; gap: 0.6rem; margin-top: 0.8rem; }
  .formulaire label { display: grid; gap: 0.25rem; font-size: 0.88rem; }
  .formulaire input, .formulaire select, .formulaire textarea { font: inherit; font-size: 16px; color: var(--foreground); background: rgb(0 0 0 / 0.35);
             border: 1px solid rgb(201 209 220 / 0.2); border-radius: 0.6rem; padding: 0.55rem 0.7rem; min-height: 2.75rem; width: 100%; }
  .panneau { position: absolute; z-index: 61; left: max(0.75rem, env(safe-area-inset-left, 0px)); top: calc(4.5rem + env(safe-area-inset-top, 0px));
             bottom: calc(4.5rem + env(safe-area-inset-bottom, 0px)); width: min(19rem, calc(100vw - 1.5rem)); display: grid;
             grid-template-rows: auto 1fr; gap: 0.5rem; padding: 0.6rem; }
  .panneau input { font: inherit; font-size: 16px; color: var(--foreground); background: rgb(0 0 0 / 0.35); border: 1px solid rgb(201 209 220 / 0.2);
                   border-radius: 0.6rem; padding: 0.5rem 0.7rem; min-height: 2.75rem; }
  .panneau ul { margin: 0; padding: 0; list-style: none; overflow-y: auto; }
  .panneau button { display: grid; width: 100%; text-align: left; gap: 0.05rem; padding: 0.45rem 0.6rem; min-height: 2.75rem; border: 0;
                    border-radius: 0.6rem; background: transparent; color: var(--foreground); font: inherit; font-size: 0.9rem; cursor: pointer; }
  .panneau button span:last-child { font-size: 0.78rem; }
  .panneau button:hover, .panneau button[aria-current='true'] { background: rgb(169 143 216 / 0.18); }
  .secours { position: absolute; inset: 0; overflow-y: auto; padding: calc(5rem + env(safe-area-inset-top, 0px)) 1rem 2rem; max-width: 40rem; margin: 0 auto; }
  .secours ul { margin: 0.3rem 0 1rem; padding: 0; list-style: none; display: grid; gap: 0.3rem; }
  @media (max-width: 640px) {
    .carte { bottom: auto; top: calc(8.5rem + env(safe-area-inset-top, 0px)); max-height: calc(100dvh - 9.5rem); }
    .panneau { top: calc(8.5rem + env(safe-area-inset-top, 0px)); }
  }
</style>
