<script>
  // 0.17 : « Pas la bonne année ? » sous une photo de l'invité (chemin, album, « Aidez-moi à dater »).
  // L'avis part à Sillage (jamais dans Immich) ; Millésime le lit, Julien décide. La photo est nommée par son
  // identifiant propre à Sillage (opaque), jamais par celui d'Immich.
  //   jeton : l'invitation ; photo : l'identifiant opaque ; annee : l'année où la photo est placée (null : pas encore datée)
  //   avis : l'état de l'avis de l'invité ({ etat: 'signale', annee, environ, mot } ou { etat: 'regardee' }) ou rien
  //   onavis(reponse) : la réponse de Sillage ({ signalements, photos_redatees }) après un envoi ou un retrait
  //   lecture : l'aperçu du propriétaire (onglet Chambres) : les marques se lisent, rien ne s'envoie
  //   libelle : le texte du bouton discret
  let { jeton, photo, annee = null, avis = null, onavis, lecture = false, libelle = 'Pas la bonne année ?' } = $props()
  let ouvert = $state(false)
  let envoi = $state(false)
  let erreur = $state('')
  let merci = $state('')
  let vers = $state('')
  let environ = $state(false)
  let mot = $state('')
  const maintenant = new Date().getFullYear()
  const id = 'sig-' + Math.random().toString(36).slice(2, 9)
  const signale = $derived(avis?.etat === 'signale')

  function ouvrir() {
    erreur = ''
    merci = ''
    vers = signale ? String(avis.annee) : ''
    environ = signale ? !!avis.environ : false
    mot = signale ? avis.mot || '' : ''
    ouvert = true
  }

  async function appel(methode, corps) {
    envoi = true
    erreur = ''
    try {
      const r = await fetch(`/api/invite/${encodeURIComponent(jeton)}/signalement/${encodeURIComponent(photo)}`, {
        method: methode,
        headers: corps ? { 'Content-Type': 'application/json' } : undefined,
        body: corps ? JSON.stringify(corps) : undefined,
      })
      let j = null
      try { j = await r.json() } catch { /* réponse sans contenu */ }
      if (!r.ok) throw new Error(j?.detail && typeof j.detail === 'string' ? j.detail : 'Sillage ne répond pas pour l\'instant.')
      onavis?.(j)
      return j
    } catch (e) {
      erreur = e.message
      return null
    } finally {
      envoi = false
    }
  }

  async function envoyer(ev) {
    ev.preventDefault()
    const a = Number(vers.trim())
    if (!/^\d{4}$/.test(vers.trim()) || a < 1900 || a > maintenant) { erreur = `Une année entre 1900 et ${maintenant}, par exemple 1987.`; return }
    const j = await appel('POST', { annee: a, environ, mot: mot.trim() })
    if (j) { ouvert = false; merci = j.message || 'Merci, c\'est transmis à Julien' }
  }

  async function retirer() {
    const j = await appel('DELETE')
    if (j) { ouvert = false; merci = '' }
  }
</script>

<div class="signaler">
  {#if ouvert}
    <form class="formulaire" onsubmit={envoyer} aria-label="Proposer une année">
      <p class="place">{annee != null ? `Photo placée en ${annee}` : 'Pas encore datée'}</p>
      <label class="champ" for={id + '-a'}>Vers quelle année ?</label>
      <div class="ligne">
        <input id={id + '-a'} class="annee" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="4" autocomplete="off"
               placeholder={annee != null ? String(annee) : '1985'} bind:value={vers} required />
        <label class="environ"><input type="checkbox" bind:checked={environ} /> environ</label>
      </div>
      <label class="champ" for={id + '-m'}>Un souvenir pour situer (facultatif)</label>
      <input id={id + '-m'} type="text" maxlength="120" placeholder="Le baptême de Léa…" bind:value={mot} />
      {#if erreur}<p class="erreur" role="alert">{erreur}</p>{/if}
      <div class="boutons">
        <button type="submit" class="principal" disabled={envoi}>{envoi ? 'Envoi…' : 'Envoyer'}</button>
        <button type="button" onclick={() => { ouvert = false; erreur = '' }}>Annuler</button>
        {#if signale}<button type="button" class="retirer" disabled={envoi} onclick={retirer}>Retirer mon avis</button>{/if}
      </div>
    </form>
  {:else if signale}
    <p class="marque">
      <span class="pastille">Signalé · {avis.environ ? 'vers ' : ''}{avis.annee}</span>
      {#if merci}<span class="merci" role="status">{merci}</span>{/if}
      {#if !lecture}<button type="button" class="discret" onclick={ouvrir}>Changer d'avis</button>{/if}
    </p>
    {#if erreur}<p class="erreur" role="alert">{erreur}</p>{/if}
  {:else}
    {#if avis?.etat === 'regardee'}<p class="regardee">Julien a regardé, la date reste.</p>{/if}
    {#if !lecture}<button type="button" class="discret" onclick={ouvrir}>{libelle}</button>{/if}
  {/if}
</div>

<style>
  .signaler { font-size: 0.85rem; }
  .discret { min-height: 2.75rem; padding: 0 0.1rem; border: 0; background: none; color: var(--muted-foreground);
    font: inherit; text-decoration: underline; text-decoration-color: color-mix(in srgb, currentColor 40%, transparent);
    text-underline-offset: 3px; text-align: left; cursor: pointer; }
  .discret:hover, .discret:focus-visible { color: var(--foreground); }
  .marque { display: flex; flex-wrap: wrap; align-items: center; gap: 0.25rem 0.75rem; margin: 0; }
  .pastille { display: inline-flex; align-items: center; min-height: 1.75rem; padding: 0 0.6rem; border-radius: 999px;
    background: color-mix(in srgb, var(--app) 18%, transparent); border: 1px solid color-mix(in srgb, var(--app) 50%, transparent);
    color: var(--foreground); font-weight: 600; font-size: 0.8rem; }
  .merci { color: var(--valide, var(--app)); }
  .regardee { margin: 0.35rem 0 0; color: var(--muted-foreground); font-style: italic; }
  .formulaire { display: grid; gap: 0.4rem; margin-top: 0.25rem; padding: 0.75rem; border-radius: 0.9rem;
    border: 1px solid var(--border); background: var(--secondary); color: var(--foreground); }
  .place { margin: 0 0 0.2rem; color: var(--muted-foreground); }
  .champ { font-weight: 600; }
  .ligne { display: flex; align-items: center; gap: 0.9rem; flex-wrap: wrap; }
  .formulaire input[type='text'] { min-height: 2.75rem; width: 100%; padding: 0 0.75rem; border-radius: 0.6rem;
    border: 1px solid var(--input); background: var(--background); color: var(--foreground); font: inherit; font-size: 1rem; }
  .formulaire input.annee { width: 6.5rem; font-variant-numeric: tabular-nums; }
  .formulaire input:focus-visible { outline: 2px solid var(--ring); outline-offset: 1px; }
  .environ { display: inline-flex; align-items: center; gap: 0.45rem; min-height: 2.75rem; cursor: pointer; }
  .environ input { width: 1.15rem; height: 1.15rem; accent-color: var(--app); }
  .boutons { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.3rem; }
  .boutons button { min-height: 2.75rem; padding: 0 1rem; border-radius: 999px; border: 1px solid var(--border);
    background: var(--card); color: var(--foreground); font: inherit; cursor: pointer; }
  .boutons .principal { background: var(--app); border-color: var(--app); color: var(--app-contraste); font-weight: 600; }
  .boutons .retirer { margin-left: auto; border-color: transparent; background: none; text-decoration: underline; text-underline-offset: 3px; }
  .boutons button:disabled { opacity: 0.6; cursor: default; }
  .erreur { margin: 0.2rem 0 0; color: var(--destructive); }
</style>
