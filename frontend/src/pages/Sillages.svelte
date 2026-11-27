<script>
  // L'écran d'ouverture : les personnes nommées d'Immich. Toucher une personne ouvre son chemin.
  import { onMount } from 'svelte'
  import Search from '@lucide/svelte/icons/search'
  import { api } from '$lib/api.js'

  let { ondeconnecte } = $props()
  let personnes = $state(null)
  let parCarnet = $state(false)
  let carnet = $state({})
  let erreur = $state('')
  let cherche = $state('')
  let aVerifier = $state(false)   // 0.10 : la tuile « À vérifier » filtre la liste

  const plat = (t) => t.toLowerCase().normalize('NFD').replace(/\p{Mn}/gu, '')
  // Avec carnet : ses fiches à l'ouverture, les proches d'abord ; les autres personnes d'Immich par la recherche.
  const sansNaissance = $derived((personnes || []).filter((p) => !p.naissance && (!parCarnet || p.carnet)))
  const montrees = $derived.by(() => {
    if (aVerifier) return sansNaissance
    const mot = plat(cherche.trim())
    const liste = (personnes || []).filter((p) => (mot ? plat(p.nom).includes(mot) : !parCarnet || p.carnet))
    return parCarnet && !mot ? [...liste.filter((p) => p.proche), ...liste.filter((p) => !p.proche)] : liste
  })

  // 0.26 : « Quoi de neuf » : photos ajoutées à Immich depuis 30 jours dans les sillages préparés (personnes de carnet)
  let neuf = $state(null)
  const anneeDe = (e) => e.debut.slice(0, 4)
  const ligne = (e) => e.nouvelle
    ? 'Nouvelle étape : ' + (e.nom ? e.nom + ', ' + anneeDe(e) : anneeDe(e)) + ' (' + e.photos + ' photo' + (e.photos > 1 ? 's' : '') + ')'
    : '+' + e.photos + ' photo' + (e.photos > 1 ? 's' : '') + ' dans ' + (e.nom ? e.nom + ', ' + anneeDe(e) : 'l\'étape de ' + anneeDe(e))
  const quandAjout = (j) => {
    const n = Math.round((new Date(new Date().toDateString()) - new Date(j + 'T00:00:00')) / 86400000)
    return n <= 0 ? 'aujourd\'hui' : n === 1 ? 'hier' : 'il y a ' + n + ' jours'
  }

  onMount(async () => {
    try { const r = await api.get('/api/personnes'); parCarnet = r.par_carnet; carnet = r.carnet || {}; personnes = r.personnes }
    catch (err) { if (err.statut === 401) ondeconnecte?.(); else erreur = err.message }
    try { neuf = await api.get('/api/nouveautes') } catch { neuf = null }
  })
</script>

<header class="mb-5 flex flex-wrap items-end justify-between gap-3">
  <div>
    <p class="etiquette">Sillage</p>
    <h1 class="titre">Sillages</h1>
  </div>
  <label class="relative w-full sm:w-64">
    <span class="sr-only">Chercher une personne</span>
    <Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
    <input type="search" bind:value={cherche} placeholder="Chercher une personne"
           class="h-10 w-full rounded-lg border border-input bg-transparent pr-3 pl-9 text-base outline-none focus:border-ring" />
  </label>
</header>

{#if erreur}
  <p class="rounded-2xl border border-destructive/50 p-4 text-sm" role="alert">{erreur}</p>
{:else if personnes === null}
  <p class="text-sm text-muted-foreground" role="status">Lecture des personnes dans Immich…</p>
{:else if !personnes.length}
  <p class="rounded-2xl border bg-card p-5 text-sm text-muted-foreground">Immich ne connaît encore aucune personne nommée. Donne un nom à un visage dans Immich : il apparaîtra ici.</p>
{:else}
  {#if carnet.erreur}
    <p class="mb-3 rounded-2xl border bg-card p-3 text-sm text-muted-foreground" role="status">{carnet.erreur} En attendant, voici les personnes nommées d'Immich.</p>
  {:else if parCarnet && !cherche.trim()}
    <p class="mb-3 text-sm text-muted-foreground">Les fiches de carnet liées à Immich. Une autre personne d'Immich ? Cherche son nom.</p>
  {/if}
  {#if neuf?.personnes?.length && !cherche.trim() && !aVerifier}
    <section class="neuf" aria-labelledby="titre-neuf">
      <h2 id="titre-neuf" class="etiquette">Quoi de neuf · {neuf.jours} derniers jours</h2>
      <ul>
        {#each neuf.personnes as p (p.personne)}
          <li>
            <img src={'/api/portrait/' + p.personne} alt="" loading="lazy" />
            <div class="min-w-0">
              <p class="font-medium">{p.nom} <small>· {quandAjout(p.ajoutee_le)}</small></p>
              <ul class="lignes">
                {#each p.etapes as e (e.cle)}
                  <li><a href={'#/chemin/' + p.personne + '/' + encodeURIComponent(e.cle)}>{ligne(e)}{e.retrouvee && !e.nouvelle ? ' · retrouvée' : ''}</a></li>
                {/each}
                {#if p.autres_etapes}<li class="reste">et {p.autres_photos} photo{p.autres_photos > 1 ? 's' : ''} dans {p.autres_etapes} autre{p.autres_etapes > 1 ? 's' : ''} étape{p.autres_etapes > 1 ? 's' : ''}</li>{/if}
              </ul>
            </div>
          </li>
        {/each}
      </ul>
    </section>
  {/if}
  {#if sansNaissance.length}
    <button type="button" class="averifier" aria-pressed={aVerifier} onclick={() => (aVerifier = !aVerifier)}>
      <span class="etiquette">À vérifier</span>
      <span><strong>{sansNaissance.length}</strong> personne{sansNaissance.length > 1 ? 's' : ''} sans date de naissance dans Immich</span>
      <small>{aVerifier ? 'Toucher pour revenir à toute la liste.' : 'Leur chemin est rangé par année au lieu de l\'âge. Ajoute la date sur leur fiche dans Immich.'}</small>
    </button>
  {/if}
  <ul class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4" aria-label="Personnes">
    {#each montrees as p (p.id)}
      <li>
        <a href={'#/chemin/' + p.id} class="flex h-full flex-col items-center gap-2 rounded-2xl border bg-card p-4 text-center transition-colors hover:border-primary">
          <img src={'/api/portrait/' + p.id} alt="" loading="lazy" class="size-20 rounded-full bg-secondary object-cover" />
          <span class="font-medium text-balance">{p.nom}</span>
          <span class="text-sm text-muted-foreground">{p.age != null ? p.age + ' ans' : p.fin ? (p.naissance ? p.naissance.slice(0, 4) + ' – ' : '† ') + p.fin.slice(0, 4) : p.naissance ? 'né(e) en ' + p.naissance.slice(0, 4) : 'date de naissance inconnue'}{parCarnet && !p.carnet ? ' · hors carnet' : ''}</span>
        </a>
      </li>
    {/each}
  </ul>
  {#if !montrees.length}<p class="text-sm text-muted-foreground">Personne ne porte ce nom.</p>{/if}
{/if}

<style>
  .neuf { margin-bottom: 1rem; padding: 0.9rem 1.1rem; border: 1px solid var(--border); border-left: 4px solid var(--app); border-radius: 1rem; background: var(--card); }
  .neuf > ul { display: grid; gap: 0.8rem; margin-top: 0.6rem; }
  .neuf > ul > li { display: flex; gap: 0.75rem; align-items: flex-start; }
  .neuf img { width: 2.6rem; height: 2.6rem; flex: none; border-radius: 50%; object-fit: cover; background: var(--secondary); }
  .neuf small { color: var(--muted-foreground); font-weight: 400; }
  .lignes { display: grid; gap: 0.15rem; font-size: 0.875rem; }
  .lignes a { color: var(--foreground); text-decoration: underline; text-decoration-color: var(--border); text-underline-offset: 3px; }
  .lignes a:hover { text-decoration-color: var(--app); }
  .lignes .reste { color: var(--muted-foreground); }
  .averifier { display: grid; gap: 0.15rem; width: 100%; margin-bottom: 1rem; padding: 0.9rem 1.1rem; text-align: left; border: 1px solid var(--border); border-left: 4px solid var(--app); border-radius: 1rem; background: var(--card); }
  .averifier[aria-pressed='true'] { border-color: var(--app); }
  .averifier small { color: var(--muted-foreground); }
</style>
