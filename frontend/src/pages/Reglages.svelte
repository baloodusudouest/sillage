<script>
  // « Réglages » : ce qui n'est pas un service. Toujours en bas : la version et la déconnexion.
  // 0.16 : les réglages d'usage quittent la stack pour cet écran (repris une fois des anciennes variables),
  // et « Restaurer les réglages » relit une sauvegarde gardée par l'Anneau.
  import { onMount } from 'svelte'
  import X from '@lucide/svelte/icons/x'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  let { session, deconnecter } = $props()

  const champ = 'w-full min-w-0 rounded-lg border bg-background px-3 text-sm'
  const NOMS = {
    mots: 'Mots des temps forts', dossiers_muets: 'Dossiers muets', cache_mo: 'Place des vignettes (Mo)',
    tag_estimee: 'Tag des dates estimées', tag_non_datee: 'Tag des scans non datés', hotes: 'Hôtes de la maison',
  }

  // ---------------------------------------------------------------- réglages du chemin
  let form = $state({ mots: '', dossiers_muets: '', cache_mo: '', tag_estimee: '', tag_non_datee: '' })
  let messageChemin = $state('')
  let enCours = $state(false)
  let charge = $state(false)     // « Garder » attend que les réglages soient lus (sinon il enverrait un formulaire vide)

  function remplir(r) {
    form = {
      mots: (r.mots || []).join(', '), dossiers_muets: (r.dossiers_muets || []).join(', '),
      cache_mo: String(r.cache_mo ?? ''), tag_estimee: r.tag_estimee || '', tag_non_datee: r.tag_non_datee || '',
    }
    hotes = r.hotes || []
    charge = true
  }
  const liste = (texte) => texte.split(',').map((x) => x.trim()).filter(Boolean)

  async function garderChemin(e) {
    e.preventDefault()
    enCours = true
    const place = form.cache_mo.trim()
    try {
      remplir(await api.put('/api/reglages', {
        mots: liste(form.mots), dossiers_muets: liste(form.dossiers_muets),
        cache_mo: /^\d+$/.test(place) ? Number(place) : place,
        tag_estimee: form.tag_estimee.trim(), tag_non_datee: form.tag_non_datee.trim(),
      }))
      messageChemin = 'Gardé. Les chemins et les frises des chambres suivent tout de suite.'
    } catch (err) { messageChemin = err.statut === 400 ? err.message : 'Pas gardé : Sillage ne répond pas.' }
    enCours = false
  }

  // ---------------------------------------------------------------- sillages préparés (0.25)
  let etatSillages = $state(null)
  let messageSillages = $state('')
  let minuteur = null
  const quand = (iso) => {
    const d = new Date(iso), auj = new Date()
    const h = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
    return d.toDateString() === auj.toDateString() ? 'aujourd\'hui à ' + h : 'le ' + d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' }) + ' à ' + h
  }
  async function lireSillages() {
    try { etatSillages = await api.get('/api/sillages') } catch { etatSillages = null }
    clearTimeout(minuteur)
    if (etatSillages?.preparation?.en_cours) minuteur = setTimeout(lireSillages, 2000)
  }
  async function preparerSillages() {
    messageSillages = ''
    try { await api.post('/api/sillages/preparer', {}); messageSillages = 'Préparation lancée, en fond.' }
    catch (err) { messageSillages = err.statut === 409 ? err.message : 'Sillage ne répond pas.' }
    setTimeout(lireSillages, 500)
  }
  onMount(() => { lireSillages(); return () => clearTimeout(minuteur) })

  // ---------------------------------------------------------------- hôtes (0.7)
  // Dans la frise de plusieurs invités, chacun garde ses photos seul ou avec eux.
  let hotes = $state([])
  let personnes = $state([])
  let choisi = $state('')
  let message = $state('')
  const libres = $derived(personnes.filter((p) => !hotes.some((h) => h.id === p.id)))

  onMount(async () => {
    try {
      remplir(await api.get('/api/reglages'))
      personnes = (await api.get('/api/personnes')).personnes
    } catch { message = 'Sillage ne répond pas pour l\'instant.' }
  })
  async function garder(ids) {
    try { hotes = (await api.put('/api/reglages', { hotes: ids })).hotes; message = 'Gardé.' }
    catch { message = 'Pas gardé : Sillage ou Immich ne répond pas.' }
  }
  const ajouter = () => { if (choisi) garder([...hotes.map((h) => h.id), choisi]); choisi = '' }

  // ---------------------------------------------------------------- restaurer (0.16)
  let dates = $state([])
  let le = $state('')
  let apercu = $state(null)        // { le, version, differences }
  let confirmer = $state(false)
  let messageRestaurer = $state('')
  let attente = $state(false)

  const montrer = (v) => Array.isArray(v) ? (v.length ? v.map((x) => x?.nom ?? x).join(', ') : '(vide)')
    : v === '' || v === null || v === undefined ? '(vide)' : String(v)

  async function voirSauvegardes() {
    attente = true; messageRestaurer = ''; apercu = null; confirmer = false
    try { dates = (await api.get('/api/restaurer')).dates; le = dates[0] || ''; if (le) await voirDifferences() }
    catch (err) { dates = []; messageRestaurer = err.message }
    attente = false
  }
  async function voirDifferences() {
    confirmer = false; messageRestaurer = ''
    if (!le) { apercu = null; return }
    try { apercu = await api.get('/api/restaurer?le=' + encodeURIComponent(le)) }
    catch (err) { apercu = null; messageRestaurer = err.message }
  }
  async function restaurer() {
    attente = true
    try {
      remplir(await api.post('/api/restaurer', { le }))
      messageRestaurer = `Réglages du ${le} restaurés.`
      apercu = null; confirmer = false
    } catch (err) { messageRestaurer = err.message }
    attente = false
  }
</script>

<header class="mb-5">
  <p class="etiquette">Sillage</p>
  <h1 class="titre">Réglages</h1>
</header>

<section class="rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Comment le chemin est fait</h2>
  <p class="mt-1 text-sm text-muted-foreground">Une étape réunit les photos d'une personne prises à moins de deux jours les unes des autres. Elle porte le nom de l'album de sa photo phare, sinon celui de son dossier, sinon sa date. Un temps fort est une étape dont le nom contient un des mots de la liste ci-dessous.</p>
</section>

<section class="mt-4 rounded-2xl border bg-card p-5" aria-labelledby="titre-chemin">
  <h2 id="titre-chemin" class="text-lg font-semibold">Le chemin</h2>
  <p class="mt-1 text-sm text-muted-foreground">Ces réglages se changent ici, sans redémarrer Sillage. Les listes se séparent par des virgules.</p>
  <form class="mt-3 grid gap-4" onsubmit={garderChemin}>
    <div class="grid gap-1">
      <label for="r-mots" class="text-sm font-medium">{NOMS.mots}</label>
      <textarea id="r-mots" rows="2" bind:value={form.mots} class="{champ} py-2"></textarea>
      <p class="text-xs text-muted-foreground">Vide : la liste de départ (mariage, baptême, anniversaire, Noël, vacances…).</p>
    </div>
    <div class="grid gap-1">
      <label for="r-muets" class="text-sm font-medium">{NOMS.dossiers_muets}</label>
      <textarea id="r-muets" rows="2" bind:value={form.dossiers_muets} class="{champ} py-2"></textarea>
      <p class="text-xs text-muted-foreground">Noms de dossier qui ne disent rien de l'évènement, en plus de ceux que Sillage connaît déjà.</p>
    </div>
    <div class="grid gap-4 sm:grid-cols-2">
      <div class="grid gap-1">
        <label for="r-estimee" class="text-sm font-medium">{NOMS.tag_estimee}</label>
        <input id="r-estimee" type="text" bind:value={form.tag_estimee} class="{champ} h-10" />
        <p class="text-xs text-muted-foreground">Début des tags que Millésime pose (« Date estimée/1975 ±3 »). Vide : pas lu.</p>
      </div>
      <div class="grid gap-1">
        <label for="r-non-datee" class="text-sm font-medium">{NOMS.tag_non_datee}</label>
        <input id="r-non-datee" type="text" bind:value={form.tag_non_datee} class="{champ} h-10" />
        <p class="text-xs text-muted-foreground">Tag complet des scans qui attendent une date. Vide : celui que règle Chambre noire, sinon pas lu.</p>
      </div>
    </div>
    <div class="grid gap-1 sm:max-w-xs">
      <label for="r-cache" class="text-sm font-medium">{NOMS.cache_mo}</label>
      <input id="r-cache" type="text" inputmode="numeric" bind:value={form.cache_mo} class="{champ} h-10" />
      <p class="text-xs text-muted-foreground">Vignettes gardées sur le disque de Sillage. 0 : aucune.</p>
    </div>
    <div class="flex flex-wrap items-center gap-3">
      <Button type="submit" disabled={enCours || !charge}>Garder</Button>
      {#if messageChemin}<p class="text-sm text-muted-foreground" role="status">{messageChemin}</p>{/if}
    </div>
  </form>
</section>

<section class="mt-4 rounded-2xl border bg-card p-5" aria-labelledby="titre-sillages">
  <h2 id="titre-sillages" class="text-lg font-semibold">Sillages préparés</h2>
  <p class="mt-1 text-sm text-muted-foreground">Le sillage de chaque personne de carnet est préparé d'avance, vérifié chaque nuit et refait en entier dans la nuit du mardi : il s'ouvre sans attendre.</p>
  {#if etatSillages}
    {@const p = etatSillages.preparation}
    <p class="mt-3 text-sm" role="status">
      {etatSillages.prets} sur {etatSillages.carnet} prêt{etatSillages.prets > 1 ? 's' : ''}{etatSillages.plus_recent ? ' · dernier préparé ' + quand(etatSillages.plus_recent) : ''}{p.fin && !p.en_cours ? ' · ' + p.refaits + ' refait' + (p.refaits > 1 ? 's' : '') + ' à la dernière préparation' : ''}
    </p>
    {#if p.en_cours}
      <p class="mt-1 text-sm text-muted-foreground">En cours : {p.faits} sur {p.total}…</p>
    {/if}
    {#if etatSillages.en_erreur || p.derniere_erreur}
      <p class="mt-1 text-sm text-destructive">{etatSillages.en_erreur ? etatSillages.en_erreur + ' sillage' + (etatSillages.en_erreur > 1 ? 's' : '') + ' pas à jour (l\'ancien reste affiché). ' : ''}{p.derniere_erreur}</p>
    {/if}
  {/if}
  <div class="mt-4">
    <Button onclick={preparerSillages} disabled={etatSillages?.preparation?.en_cours}>Préparer les sillages maintenant</Button>
  </div>
  {#if messageSillages}<p class="mt-2 text-sm text-muted-foreground" role="status">{messageSillages}</p>{/if}
</section>

<section class="mt-4 rounded-2xl border bg-card p-5" aria-labelledby="titre-hotes">
  <h2 id="titre-hotes" class="text-lg font-semibold">Hôtes de la maison</h2>
  <p class="mt-1 text-sm text-muted-foreground">Quand une chambre reçoit plusieurs invités, leur frise montre les moments où ils sont ensemble, et pour chacun ses photos seul ou avec les hôtes. Une photo où il y a quelqu'un d'autre n'y entre pas.</p>
  <ul class="mt-3 flex flex-wrap gap-2" aria-label="Hôtes choisis">
    {#each hotes as h (h.id)}
      <li class="flex items-center gap-1 rounded-full border bg-secondary py-1 pr-1 pl-3 text-sm">
        {h.nom}
        <button type="button" class="grid size-8 place-items-center rounded-full hover:bg-background" aria-label={'Retirer ' + h.nom}
                onclick={() => garder(hotes.filter((x) => x.id !== h.id).map((x) => x.id))}><X class="size-4" aria-hidden="true" /></button>
      </li>
    {:else}
      <li class="text-sm text-muted-foreground">Aucun hôte : chaque invité ne garde que ses photos seul.</li>
    {/each}
  </ul>
  <div class="mt-3 flex flex-wrap items-center gap-2">
    <label for="hote" class="sr-only">Ajouter un hôte</label>
    <select id="hote" bind:value={choisi} class="h-10 min-w-0 flex-1 rounded-lg border bg-background px-3 text-sm sm:max-w-xs">
      <option value="">Ajouter un hôte…</option>
      {#each libres as p (p.id)}<option value={p.id}>{p.nom}</option>{/each}
    </select>
    <Button variant="outline" onclick={ajouter} disabled={!choisi}>Ajouter</Button>
  </div>
  {#if message}<p class="mt-2 text-sm text-muted-foreground" role="status">{message}</p>{/if}
</section>

<section class="mt-4 rounded-2xl border bg-card p-5" aria-labelledby="titre-restaurer">
  <h2 id="titre-restaurer" class="text-lg font-semibold">Restaurer les réglages</h2>
  <p class="mt-1 text-sm text-muted-foreground">L'Anneau garde chaque nuit une copie de ces réglages. Choisis une date, regarde ce qui changerait, puis confirme. Seuls les réglages de Sillage changent.</p>
  <div class="mt-3 flex flex-wrap items-center gap-2">
    <Button variant="outline" onclick={voirSauvegardes} disabled={attente}>Voir les sauvegardes</Button>
    {#if dates.length}
      <label for="r-date" class="sr-only">Date de la sauvegarde</label>
      <select id="r-date" bind:value={le} onchange={voirDifferences} class="h-10 min-w-0 flex-1 rounded-lg border bg-background px-3 text-sm sm:max-w-xs">
        {#each dates as d (d)}<option value={d}>{d}</option>{/each}
      </select>
    {/if}
  </div>
  {#if apercu}
    {#if apercu.differences.length}
      <ul class="mt-3 grid gap-2" aria-label="Différences avec la sauvegarde">
        {#each apercu.differences as d (d.cle)}
          <li class="rounded-lg border bg-background p-3 text-sm">
            <p class="font-medium">{NOMS[d.cle] || d.cle}</p>
            <p class="mt-1 break-words text-muted-foreground">{montrer(d.actuel)} <span aria-hidden="true">→</span><span class="sr-only">devient</span> <span class="text-foreground">{montrer(d.sauve)}</span></p>
          </li>
        {/each}
      </ul>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        {#if !confirmer}
          <Button onclick={() => (confirmer = true)}>Restaurer ces réglages</Button>
        {:else}
          <Button onclick={restaurer} disabled={attente}>Confirmer</Button>
          <Button variant="outline" onclick={() => (confirmer = false)}>Annuler</Button>
        {/if}
      </div>
    {:else}
      <p class="mt-3 text-sm text-muted-foreground" role="status">Rien à restaurer : les réglages sont déjà ceux du {apercu.le.slice(0, 10)}.</p>
    {/if}
  {/if}
  {#if messageRestaurer}<p class="mt-2 text-sm text-muted-foreground" role="status">{messageRestaurer}</p>{/if}
</section>

<p class="mt-6 flex items-center justify-between gap-3 text-sm text-muted-foreground">
  <span>Sillage {session.version}</span>
  <Button variant="outline" onclick={deconnecter}>Se déconnecter</Button>
</p>
