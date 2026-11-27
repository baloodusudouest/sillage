<script>
  // L'arbre de famille, en plein écran par-dessus le chemin (0.22). 0.23 : cinq vues validées par Julien le 27/11/2026
  // — à plat : Éventail, Sablier, Arbre (complet) ; en 3D : Arbre de vie, Hélice (la constellation est retirée) — et le
  // champ « Lien avec… » : une deuxième personne, le lien en clair, le chemin qui s'allume sur l'arbre (par le sang
  // d'abord, sinon par les couples), les étapes écrites dessous.
  // Toucher une personne : elle passe au centre et sa carte s'ouvre. Propriétaire : « Voir son sillage », « Ouvrir dans
  // carnet » (ou Treemich). Invité : « Proposer une correction » (envoyée à carnet par Sillage).
  // three.js n'est chargé qu'à l'ouverture d'une vue 3D.
  import { onMount, onDestroy, tick } from 'svelte'
  import Croix from '$lib/Croix.svelte'
  import { dateLongue } from '$lib/dates.js'
  import { indexer, parente } from '$lib/arbre/parente.js'
  import { chemin as cheminEntre, famille, motEtape, nomDe, prenomNom, surlignage } from '$lib/arbre/famille.js'
  import { creerVues2D } from '$lib/arbre/vues2d.js'

  let { arbre, invite = null, apercu = false, restantes = 0, onfermer } = $props()
  // invite : { jeton } pour un invité ; null pour le propriétaire

  const VUES = [
    { cle: 'eventail', nom: 'Éventail', plat: true },
    { cle: 'sablier', nom: 'Sablier', plat: true },
    { cle: 'complet', nom: 'Arbre', plat: true },
    { cle: 'vie', nom: 'Vie 3D', plat: false },
    { cle: 'helice', nom: 'Hélice', plat: false },
  ]
  const CLE_VUE = 'sillage-arbre-vue'
  const CLE_AIDE = 'sillage-arbre-aide-2'
  const lireStock = (k) => { try { return localStorage.getItem(k) } catch { return null } }
  const ecrireStock = (k, v) => { try { localStorage.setItem(k, v) } catch { /* navigation privée */ } }

  // Les visages passent par Sillage (identifiants opaques pour un invité)
  const donnees = {
    depart: arbre.depart, liens: arbre.liens,
    personnes: arbre.personnes.map((p) => ({ ...p, visage: !p.visage ? null
      : invite ? `/api/invite/${encodeURIComponent(invite.jeton)}/arbre/vignette/${p.id}` : `/api/arbre/vignette/${p.visage}` })),
  }
  const fam = famille(donnees)
  const ix = indexer(arbre.personnes, arbre.liens)
  const parId = new Map(arbre.personnes.map((p) => [p.id, p]))

  let svgEl = $state(null)
  let boite = $state(null)
  let moteur = null                         // vues à plat, arbre de vie ou hélice
  let vue = $state(VUES.some((v) => v.cle === lireStock(CLE_VUE)) ? lireStock(CLE_VUE) : 'eventail')
  let avec3d = $state(true)
  let centre = $state(arbre.depart)         // la personne au centre de la vue
  let reference = $state(arbre.depart)      // d'où se lisent les liens des cartes (la personne de départ, ou l'invité choisi)
  let choisie = $state(null)
  let aide = $state(lireStock(CLE_AIDE) !== 'vu')
  let pret = $state(false)
  let perdu = $state(false)
  let dessines = $state(new Set())
  let formulaire = $state(null)
  let envoi = $state({ attente: false, message: '', erreur: '' })
  let reste = $state(restantes)
  let panneau = $state(null)                // 'liste' | 'lien' | null
  let cherche = $state('')
  let cible = $state(null)                  // « Lien avec… » : la deuxième personne

  // 0.23.1 : un chemin que la vue ne peut pas montrer en entier (éventail, sablier, arbre de vie) s'affiche en schéma
  // de parenté, de la personne au centre jusqu'à la personne cherchée
  const schema = $derived(!!cible && !['complet', 'helice'].includes(vue))
  const plat = $derived(VUES.find((v) => v.cle === vue)?.plat || schema)
  const titre = $derived(invite ? 'Votre arbre de famille' : `L'arbre de ${nomDe(parId.get(arbre.depart))}`)
  const lien = $derived(choisie ? parente(ix, reference, choisie.id) : '')
  const prenomDe = (id) => prenomNom(parId.get(id))[0]
  const ch = $derived(cible ? cheminEntre(fam, centre, cible) : null)
  const sur = $derived(surlignage(ch, fam))
  const resume = $derived.by(() => {
    if (!cible) return null
    if (!ch) return { phrase: `${prenomDe(cible)} et ${prenomDe(centre)} ne sont pas reliés dans l'arbre.`, etapes: [] }
    const mot = parente(ix, centre, cible)
    return {
      phrase: mot === 'Par alliance' ? `${nomDe(parId.get(cible))} est de la famille de ${prenomDe(centre)} par alliance`
        : `${nomDe(parId.get(cible))} : ${phraseLien(mot, prenomDe(centre))}${ch.alliance && !/^(Belle|Beau|Gendre|Ex-|Conjoint)/.test(mot) && !/par alliance$/.test(mot) ? ' (par alliance)' : ''}`,
      etapes: ch.etapes.map((e, i) => (i ? motEtape(fam, e, ch.etapes[i - 1].id) : prenomDe(e.id))),
      incomplet: ![...sur.ids].every((id) => dessines.has(id)),
    }
  })

  // « 1985 » → « Né en 1985 » ; « 1985-03-14 » → « Née le 14 mars 1985 »
  function dates(p) {
    if (!p || p.statut === 'masque') return ''
    const e = p.genre === 'femme' ? 'e' : p.genre === 'homme' ? '' : '(e)'
    const n = p.naissance ? (p.naissance.length >= 10 ? `Né${e} le ${dateLongue(p.naissance.slice(0, 10))}` : `Né${e} en ${p.naissance.slice(0, 4)}`) : ''
    const d = p.deces === 'inconnue' ? `décédé${e}` : p.deces ? (p.deces.length >= 10 ? `décès le ${dateLongue(p.deces.slice(0, 10))}` : `décès en ${p.deces.slice(0, 4)}`) : ''
    return [n, d].filter(Boolean).join(' · ') || (p.statut === 'mineur' || p.statut === 'inconnu' ? '' : 'Dates inconnues')
  }
  const conjointsDe = (id) => fam.conjoints(id).map((x) => parId.get(x)).filter(Boolean)

  // ---------------------------------------------------------------- moteurs de dessin
  function demonter() { moteur?.m.detruire(); moteur = null }
  async function monter() {
    demonter()
    pret = false
    await tick()
    if (plat) {
      moteur = { sorte: 'plat', m: creerVues2D(svgEl, fam, { surChoix: schema ? () => {} : choisir }) }
      dessiner()
      pret = true
      return
    }
    const quoi = vue
    const { webglPossible } = await import('$lib/arbre/scene.js')
    if (!webglPossible()) { avec3d = false; vue = 'eventail'; return monter() }
    const module = quoi === 'vie' ? await import('$lib/arbre/vie.js') : await import('$lib/arbre/scene.js')
    if (quoi !== vue) return
    try {
      if (quoi === 'vie') {
        moteur = { sorte: 'vie', m: module.creerVie(boite, fam, { lienDe: (id) => (id === centre ? '' : parente(ix, centre, id)), surChoix: surChoix3d }) }
      } else {
        moteur = { sorte: 'helice', m: module.creerScene(boite, donnees, { surChoix: (p, q) => surChoix3d(p?.id ?? null, q) }) }
      }
      dessiner()
      pret = true
    } catch { avec3d = false; vue = 'eventail'; monter() }
  }
  function dessiner(garderCadre = false) {
    if (!moteur) return
    if (moteur.sorte === 'plat') dessines = schema && ch
      ? moteur.m.dessiner('chemin', centre, sur, false, { ch, lienDe: (id) => parente(ix, centre, id) })
      : moteur.m.dessiner(schema ? 'complet' : vue, centre, sur, garderCadre)
    else if (moteur.sorte === 'vie') dessines = moteur.m.montrer(centre, sur)
    else { moteur.m.surligner(sur); dessines = new Set(arbre.personnes.map((p) => p.id)) }
  }
  function surChoix3d(id, quoi) {
    if (quoi === 'perdu') { perdu = true; return }
    if (id) choisir(id)
    else fermerCarte()
  }

  // ---------------------------------------------------------------- actions
  function choisir(id) {
    const p = parId.get(id)
    if (!p) return
    choisie = p
    formulaire = null
    envoi = { attente: false, message: '', erreur: '' }
    fermerAide()
    if (moteur?.sorte === 'helice') { moteur.m.choisir(id); return }
    if (id !== centre) { centre = id; dessiner() }
  }
  function basculer(v) {
    if (v === vue) return
    vue = v
    choisie = null
    formulaire = null
    ecrireStock(CLE_VUE, v)
    monter()
  }
  function fermerAide() { aide = false; ecrireStock(CLE_AIDE, 'vu') }
  function fermerCarte() { choisie = null; formulaire = null; if (moteur?.sorte === 'helice') moteur.m.relacher() }
  function revenir() { centre = reference; choisie = null; dessiner() }
  function recentrer(id) { reference = id; centre = id; choisie = null; dessiner(); if (moteur?.sorte === 'helice') moteur.m.choisir(id) }
  function ouvrirPanneau(quoi) { panneau = panneau === quoi ? null : quoi; cherche = '' }
  function depuisListe(p) {
    if (matchMedia('(max-width: 640px)').matches) panneau = null
    choisir(p.id)
  }
  async function lienAvec(p) {
    const avant = schema
    cible = p.id
    panneau = null
    choisie = null
    await tick()
    if (schema !== avant || (schema && moteur?.sorte !== 'plat')) monter()
    else dessiner(vue === 'helice')
  }
  async function effacerLien() {
    const avant = schema
    cible = null
    await tick()
    if (avant) monter()
    else dessiner(true)
  }
  // « Cousin de sa mère » + Camille → « cousin de la mère de Camille » (0.23.1)
  function phraseLien(mot, prenom) {
    if (mot.endsWith(' par alliance')) return phraseLien(mot.slice(0, -13), prenom) + ' par alliance'
    const m = mot.toLowerCase()
    for (const [fin, dit] of [[' de sa mère', ' de la mère de '], [' de son père', ' du père de '], [" d'un parent", " d'un parent de "]])
      if (m.endsWith(fin)) return m.slice(0, -fin.length) + dit + prenom
    return m + ' de ' + prenom
  }
  function voirComplet() { vue = 'complet'; ecrireStock(CLE_VUE, 'complet'); monter() }
  // Changer de vue pendant un chemin : le schéma reste pour éventail, sablier et arbre de vie

  const trouves = $derived.by(() => {
    const t = cherche.trim().toLowerCase()
    return [...arbre.personnes]
      .filter((p) => (panneau !== 'lien' || (p.id !== centre && p.statut !== 'masque')) && (!t || nomDe(p).toLowerCase().includes(t)))
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

  const surTouche = (ev) => {
    if (ev.key !== 'Escape') return
    if (formulaire) formulaire = null
    else if (panneau) panneau = null
    else if (choisie) fermerCarte()
    else if (cible) effacerLien()
    else onfermer?.()
  }

  onMount(() => { document.documentElement.style.overflow = 'hidden'; monter() })
  onDestroy(() => { demonter(); document.documentElement.style.overflow = '' })
</script>

<svelte:window onkeydown={surTouche} />

<div class="arbre" role="dialog" aria-modal="true" aria-label={titre}>
  {#if plat}
    <svg class="plan" bind:this={svgEl} aria-label="Arbre de famille" xmlns="http://www.w3.org/2000/svg"></svg>
  {:else}
    <div class="scene" bind:this={boite} aria-hidden="true"></div>
  {/if}

  <header class="haut">
    <div class="verre titre-arbre">
      <span class="etiquette">Arbre</span>
      <span class="nom">{titre}</span>
    </div>
    <div class="verre vues" role="group" aria-label="Vue de l'arbre">
      {#each VUES.filter((v) => v.plat || avec3d) as v (v.cle)}
        <button type="button" aria-pressed={vue === v.cle} onclick={() => basculer(v.cle)}>{v.nom}</button>
      {/each}
    </div>
    <div class="outils">
      <div class="verre bascule"><button type="button" aria-pressed={panneau === 'lien'} onclick={() => ouvrirPanneau('lien')}>Lien avec…</button></div>
      <div class="verre bascule"><button type="button" aria-pressed={panneau === 'liste'} onclick={() => ouvrirPanneau('liste')}>Liste</button></div>
      {#if centre !== reference && vue !== 'helice'}
        <div class="verre bascule"><button type="button" onclick={revenir}>Revenir à {prenomDe(reference)}</button></div>
      {/if}
    </div>
  </header>
  <Croix label="Fermer l'arbre" onclick={() => onfermer?.()} />

  {#if invite && arbre.invites?.length > 1}
    <ul class="verre legende" aria-label="Lire les liens depuis">
      {#each arbre.invites as i}
        <li><button type="button" aria-pressed={reference === i.id} onclick={() => recentrer(i.id)}>{i.prenom || 'Invité'}</button></li>
      {/each}
    </ul>
  {/if}

  {#if perdu}
    <p class="verre message" role="alert">L'affichage 3D s'est arrêté. Choisissez une vue à plat, ou fermez l'arbre et rouvrez-le.</p>
  {:else if !pret}
    <p class="verre message" role="status">Préparation de l'arbre…</p>
  {:else if aide}
    <div class="verre aide" role="note">
      <p><strong>Touchez une personne</strong> pour la mettre au centre.</p>
      <p class="discret">Glissez pour vous déplacer, pincez pour zoomer. « Lien avec… » montre comment deux personnes sont parentes.</p>
      <button type="button" class="plein" onclick={fermerAide}>Compris</button>
    </div>
  {/if}

  {#if panneau}
    <nav class="verre panneau" aria-label={panneau === 'lien' ? `Lien de ${prenomDe(centre)} avec…` : "Personnes de l'arbre"}>
      {#if panneau === 'lien'}<p class="discret petit-titre">Quel lien entre <strong>{prenomDe(centre)}</strong> et…</p>{/if}
      <input type="search" bind:value={cherche} placeholder="Chercher un nom" aria-label="Chercher un nom" autocomplete="off" />
      <ul>
        {#each trouves as p (p.id)}
          <li><button type="button" aria-current={(panneau === 'lien' ? cible : choisie?.id) === p.id ? 'true' : undefined}
                      onclick={() => (panneau === 'lien' ? lienAvec(p) : depuisListe(p))}>
            <span>{nomDe(p)}</span><span class="discret">{parente(ix, reference, p.id)}</span></button></li>
        {/each}
      </ul>
    </nav>
  {/if}

  {#if resume}
    <section class="verre resultat" aria-label="Lien de parenté" aria-live="polite">
      <button type="button" class="fermer" aria-label="Effacer le lien" onclick={effacerLien}>×</button>
      <p class="phrase">{resume.phrase}</p>
      {#if resume.etapes.length}
        <ol class="etapes">
          {#each resume.etapes as e, i}<li>{#if i}<span class="fleche" aria-hidden="true">→</span>{/if}{e}</li>{/each}
        </ol>
      {/if}
      {#if schema}
        <p class="discret petit">Schéma du chemin. <button type="button" class="lien-texte" onclick={voirComplet}>Le voir dans l'arbre complet</button>
          · <button type="button" class="lien-texte" onclick={effacerLien}>Revenir à la vue</button></p>
      {/if}
    </section>
  {/if}

  {#if choisie}
    <section class="verre carte" aria-label={nomDe(choisie)}>
      <button type="button" class="fermer" aria-label="Fermer la carte" onclick={fermerCarte}>×</button>
      {#if lien}<p class="lien">{lien}{choisie.id !== reference ? ` de ${prenomDe(reference)}` : ''}</p>{/if}
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

  {#if plat}
    <p class="legende-traits" aria-hidden="true"><span><i></i>Parents et enfants</span><span><i class="c"></i>Couple</span><span><i class="x"></i>Ex-couple</span><span>Gris : décédé</span></p>
  {/if}
</div>

<style>
  .arbre { position: fixed; inset: 0; z-index: 60; background: #0b0910; color: var(--foreground); }
  .scene, .plan { position: absolute; inset: 0; width: 100%; height: 100%; }
  .plan { touch-action: none; cursor: grab; }
  .plan :global(text) { font-family: Inter, system-ui, sans-serif; pointer-events: none; }
  .plan :global(.personne) { cursor: pointer; }
  .scene :global(canvas) { display: block; }
  .verre { background: rgb(24 20 38 / 0.86); border: 1px solid rgb(201 209 220 / 0.14); border-radius: 1rem;
           backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); box-shadow: 0 10px 40px rgb(0 0 0 / 0.45); }
  .haut { position: absolute; z-index: 61; top: calc(0.75rem + env(safe-area-inset-top, 0px)); left: max(0.75rem, env(safe-area-inset-left, 0px));
          right: calc(4.25rem + env(safe-area-inset-right, 0px)); display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; pointer-events: none; }
  .haut > * { pointer-events: auto; }
  .titre-arbre { display: grid; padding: 0.45rem 0.9rem; min-width: 0; max-width: 100%; }
  .titre-arbre .nom { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .vues { display: flex; gap: 0.2rem; padding: 0.25rem; max-width: 100%; overflow-x: auto; }
  .outils { display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .bascule, .legende { display: flex; gap: 0.25rem; padding: 0.25rem; }
  .vues button, .bascule button, .legende button { min-height: 2.5rem; padding: 0 0.8rem; border-radius: 0.75rem; border: 0; background: transparent;
                                     color: var(--foreground); font: inherit; font-size: 0.88rem; cursor: pointer; white-space: nowrap; }
  .vues button[aria-pressed='true'], .bascule button[aria-pressed='true'], .legende button[aria-pressed='true'] { background: var(--app); color: var(--app-contraste); font-weight: 600; }
  .legende { position: absolute; z-index: 61; right: max(0.75rem, env(safe-area-inset-right, 0px)); bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
             list-style: none; margin: 0; flex-wrap: wrap; max-width: calc(100vw - 1.5rem); }
  .message, .aide { position: absolute; z-index: 61; left: 50%; top: 50%; transform: translate(-50%, -50%); padding: 1rem 1.2rem;
                    width: min(22rem, calc(100vw - 2rem)); text-align: center; }
  .aide p { margin: 0 0 0.5rem; }
  .carte { position: absolute; z-index: 62; right: max(0.75rem, env(safe-area-inset-right, 0px)); bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
           width: min(22rem, calc(100vw - 1.5rem)); max-height: calc(100dvh - 9rem); overflow-y: auto; padding: 1rem 1.1rem; }
  .resultat { position: absolute; z-index: 62; left: max(0.75rem, env(safe-area-inset-left, 0px)); bottom: calc(2.6rem + env(safe-area-inset-bottom, 0px));
              width: min(30rem, calc(100vw - 1.5rem)); padding: 0.9rem 1.1rem; }
  .phrase { margin: 0; padding-right: 2.2rem; font-weight: 600; color: var(--app); }
  .etapes { list-style: none; margin: 0.45rem 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.2rem 0.35rem; font-size: 0.88rem; }
  .fleche { color: var(--muted-foreground); margin-right: 0.35rem; }
  .lien-texte { background: none; border: 0; padding: 0; color: var(--app); font: inherit; text-decoration: underline; cursor: pointer; min-height: 2.75rem; }
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
  .panneau { position: absolute; z-index: 63; left: max(0.75rem, env(safe-area-inset-left, 0px)); top: calc(8.5rem + env(safe-area-inset-top, 0px));
             bottom: calc(4.5rem + env(safe-area-inset-bottom, 0px)); width: min(19rem, calc(100vw - 1.5rem)); display: grid;
             grid-template-rows: auto auto 1fr; gap: 0.5rem; padding: 0.6rem; }
  .petit-titre { margin: 0.1rem 0.3rem 0; font-size: 0.85rem; }
  .panneau input { font: inherit; font-size: 16px; color: var(--foreground); background: rgb(0 0 0 / 0.35); border: 1px solid rgb(201 209 220 / 0.2);
                   border-radius: 0.6rem; padding: 0.5rem 0.7rem; min-height: 2.75rem; }
  .panneau ul { margin: 0; padding: 0; list-style: none; overflow-y: auto; }
  .panneau button { display: grid; width: 100%; text-align: left; gap: 0.05rem; padding: 0.45rem 0.6rem; min-height: 2.75rem; border: 0;
                    border-radius: 0.6rem; background: transparent; color: var(--foreground); font: inherit; font-size: 0.9rem; cursor: pointer; }
  .panneau button span:last-child { font-size: 0.78rem; }
  .panneau button:hover, .panneau button[aria-current='true'] { background: rgb(169 143 216 / 0.18); }
  .legende-traits { position: absolute; z-index: 60; left: max(0.75rem, env(safe-area-inset-left, 0px)); bottom: calc(0.6rem + env(safe-area-inset-bottom, 0px));
                    margin: 0; display: flex; gap: 0.8rem; flex-wrap: wrap; font-size: 0.72rem; color: var(--muted-foreground); pointer-events: none; }
  .legende-traits span { display: inline-flex; align-items: center; gap: 0.35rem; }
  .legende-traits i { display: inline-block; width: 1.1rem; border-top: 2px solid var(--app); }
  .legende-traits i.c { border-color: #c9d1dc; }
  .legende-traits i.x { border-top-style: dashed; border-color: #c9d1dc; }
  @media (max-width: 640px) {
    .carte { bottom: auto; top: calc(11.5rem + env(safe-area-inset-top, 0px)); max-height: calc(100dvh - 15rem); }
    .panneau { top: calc(11.5rem + env(safe-area-inset-top, 0px)); }
    .vues button { padding: 0 0.6rem; font-size: 0.82rem; }
  }
</style>
