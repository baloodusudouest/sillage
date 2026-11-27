# Sillage

Le chemin de vie d'une personne, lu dans Immich : ses photos rangées en étapes, les étapes en chapitres d'âge. Ancien nom : Frise.

**État : 0.17.0. Sillage ne fait que lire Immich ; les corrections et les réglages sont gardés chez lui.** Voir [`REPRISE.md`](REPRISE.md) et [`docs/dossier.md`](docs/dossier.md).

## Ce que fait Sillage

- La liste des personnes : les fiches de carnet liées à Immich si carnet est réglé, sinon les personnes nommées d'Immich ; avec une recherche.
- Le chemin d'une personne : une étape réunit ses photos prises à moins de deux jours les unes des autres ; elle porte le nom de l'album de sa photo phare, sinon celui de son dossier, sinon sa date. Chapitres par décennie d'âge (par année sans date de naissance).
- « Temps forts » (étapes dont le nom contient un mot de la liste) ou « Tout ».
- Une étape ouverte : sa galerie, chaque photo en grand, un lien vers Immich.
- Corrections à la main : nommer ou masquer une étape, choisir la photo phare, retirer une photo, « ce n'est pas cette personne ».
- Les images passent par Sillage, derrière le mot de passe. Ce qui est à la corbeille, archivé ou verrouillé dans Immich n'est pas montré.

Sillage n'écrit rien dans Immich : un test le vérifie.

## Installer

Image : `ghcr.io/baloodusudouest/sillage:latest`, port 8093. Service et variables : [`docker-compose.yml`](docker-compose.yml) et [`.env.example`](.env.example).

Clé d'API à créer dans Immich pour Sillage, avec ces seuls droits : `person.read`, `asset.read`, `asset.view`, `album.read`, `tag.read`.

Variables lues : `MAISON_PASSWORD`, `MAISON_JETON` (communes à la maison), `SILLAGE_IMMICH_URL`, `SILLAGE_IMMICH_CLE`, `SILLAGE_CARNET_URL`, `SILLAGE_JETON_HA` ; facultatives : `SILLAGE_HEURE_FRISES` (2 h), `MAISON_ANNEAU_URL` (`http://anneau:8094`).

## Réglages et sauvegarde (0.16)

- Les réglages d'usage se changent dans l'écran **Réglages**, sans redémarrer : mots des temps forts, dossiers muets, tag des dates estimées, tag des scans non datés (vide : celui que règle Chambre noire, lu par `GET /externe/noms` avec le jeton commun), place des vignettes, hôtes de la maison. Fichier `/data/reglages.json` (les hôtes restent dans `sillage.db`).
- Au premier démarrage de la 0.16, chaque réglage absent du fichier est repris une fois de son ancienne variable (`SILLAGE_MOTS`, `SILLAGE_DOSSIERS_MUETS`, `SILLAGE_CACHE_MO`, `SILLAGE_TAG_ESTIMEE`, `SILLAGE_TAG_NON_DATEE`), puis ces variables ne sont plus lues.
- `GET /externe/sauvegarde` (jeton commun `MAISON_JETON` ; vide : adresse fermée) rend les réglages à l'Anneau, qui les garde chaque nuit. Jamais de variable, de chemin ni de secret.
- **Restaurer les réglages** (écran Réglages) : choisir une date gardée par l'Anneau, voir les différences, confirmer.
- Lien « Ouvrir dans Immich » : l'adresse de la tuile « Immich » de l'Anneau ; sinon le même hôte que Sillage, port 2283.

## Dates signalées par les invités (0.17)

- Sur sa page (`/invite/<jeton>`), sous chaque photo du chemin et de « Voir l'album », l'invité trouve « Pas la bonne année ? » : « Vers quelle année ? » (1900 à l'année en cours), case « environ », « Un souvenir pour situer » (facultatif, 120 caractères, texte brut). La photo reste en place avec la marque « signalé » et « Changer d'avis » tant que l'avis n'est pas traité. Écarté par Julien : « Julien a regardé, la date reste » pendant 30 jours. Merci : « Grâce à vous, N photos ont retrouvé leur année. »
- En bas de la page, **« Aidez-moi à dater »** : jusqu'à 12 photos où un invité figure et qui restent hors du chemin faute de date (tag des scans non datés, sans estimation de Millésime).
- Un avis en attente par invitation et par photo (renvoyer remplace) ; **100 avis en attente par invitation** au plus (au-delà : 429, « Julien a déjà beaucoup de photos à regarder : revenez un peu plus tard. »). Avis traités effacés 90 jours après leur traitement (au démarrage et chaque nuit). Les avis d'une invitation expirée restent jusqu'à leur traitement.
- Côté invité, une photo est nommée par un **identifiant propre à Sillage** (24 caractères, HMAC de l'invitation et de la photo, clé tirée une fois et gardée dans `sillage.db`) : jamais l'identifiant Immich, ni dans les réponses ni dans les adresses (`/api/invite/<jeton>/vignette/<id>`, `/album/<id>`, `/signalement/<id>`).
- Routes invité (sans mot de passe, le jeton de l'invitation ouvre) : `POST /api/invite/<jeton>/signalement/<id>` (`{"annee": 1987, "environ": true, "mot": "…"}`) et `DELETE` de la même adresse (changer d'avis). Réponse : `{"signalements": {<id>: {"etat": "signale" | "regardee", …}}, "photos_redatees": N}`.
- Sillage n'écrit toujours rien dans Immich : **Millésime** lit les avis et, sur « Accepter » de Julien, écrit la date.

### Contrat 1 avec Millésime (jeton commun `MAISON_JETON` ; vide : adresse fermée, 404)

- `GET /externe/signalements` → `{"contrat": 1, "signalements": [{"id": "<id Sillage>", "asset": "<id Immich>", "annee": 1987, "environ": true, "mot": "baptême…", "date_affichee": "1985-07-01" | null, "invites": ["Prénom", …], "le": "2026-11-18T10:00:00+01:00"}]}` : seulement les avis non traités. `date_affichee` : la date que l'invité voyait (null pour une photo pas encore datée, dont « Aidez-moi à dater »).
- `POST /externe/signalements/traite` avec `{"asset": "<id Immich>", "issue": "acceptee" | "corrigee" | "ecartee"}` → `{"fermes": n}` : ferme tous les avis non traités de cette photo (toutes invitations) ; rejouable (deuxième appel : `{"fermes": 0}`, code 200).

### Contrat 1 avec la Gazette (0.20 ; jeton commun `MAISON_JETON` ; vide : adresse fermée, 404)

- `GET /externe/personnes/<id Immich>/etapes` → `{"contrat": 1, "etapes": [{"nom": "Baptême de Camille", "annee": 1987, "photos": 3}]}` : les étapes nommées du chemin de cette personne, pour les suggestions « à valider » de la fiche complète de la Gazette. Mêmes règles que le chemin (photos visibles seulement, corrections de Julien comprises) ; étapes masquées et étapes sans nom écartées ; les plus fournies d'abord (à égalité, la plus ancienne), **60 au plus**. Personne inconnue de Sillage (ou identifiant mal formé) : `{"contrat": 1, "etapes": []}`, code 200. Lecture seule.

## Arbre de famille en 3D (0.22)

Sur le chemin d'une personne, le bouton **Arbre** ouvre son arbre relié (toutes les personnes reliées par un lien dans Treemich), en plein écran. Depuis la 0.23, cinq vues : à plat **Éventail**, **Sablier** et **Arbre** (complet) ; en 3D **Vie 3D** (arbre de vie, un étage par génération, sève qui descend des parents vers les enfants) et **Hélice**. Toucher une personne la met au centre. « Lien avec… » dit le lien de parenté avec une autre personne et allume le chemin sur l'arbre (par le sang d'abord, sinon par les couples). « Liste » montre et cherche les personnes ; la dernière vue est gardée sur l'appareil. Pas de lien dans Treemich : pas de bouton. L'arbre vient de carnet 3.6 (`GET /sillage/arbre`, jeton commun `MAISON_JETON`), gardé dix minutes ; three.js n'est chargé qu'à l'ouverture.

- **Propriétaire** (`GET /api/arbre/<id Immich>`, `GET /api/arbre/vignette/<id Immich>`) : nom, dates, lien de parenté ; « Voir son sillage », « Ouvrir dans carnet » (ou Treemich), selon l'annuaire de l'Anneau.
- **Invités** (`GET /api/invite/<jeton>/arbre`, `…/arbre/vignette/<id>`) : un seul arbre pour la chambre, invités mis en avant. Masquage décidé par Sillage avant l'envoi : décédé (ou né il y a plus de 100 ans) = tout ; vivant majeur = nom, visage, année de naissance ; mineur ou âge inconnu = prénom seul, ni visage ni date ; case « jamais aux invités » de carnet = un point sans nom. Ni identifiant de Treemich, de carnet ni d'Immich côté invité. Plus rien après la fin du séjour (le jeton expire).
- **Propositions des invités** (`POST /api/invite/<jeton>/arbre/proposition`) : date, nom, lien ou personne manquante, avec un mot ; 20 par invitation. Gardées par Sillage et envoyées à carnet (`POST /sillage/propositions`) ; carnet muet : renvoyées à la proposition suivante ou la nuit. Julien décide dans carnet › À traiter › Propositions d'invités ; rien n'est écrit sans lui.

## Tests

```
pip install -r requirements-dev.txt && python -m pytest tests --ignore=tests/interface
cd frontend && npm ci && npx vite build --outDir ../app/static && cd .. && python -m pytest tests/interface
```

Toutes les personnes et photos des tests sont inventées.

## La sonde d'Immich (étape 0, novembre 2026)

Image : `ghcr.io/baloodusudouest/frise:sonde`. Le conteneur tourne une fois, écrit un rapport, puis s'arrête. Il ne modifie rien dans Immich.

### Ce qu'elle mesure

| Question | Mesure |
|---|---|
| La clé suffit-elle ? | Version d'Immich, accès refusés étape par étape |
| Qui peut avoir une frise ? | Personnes nommées, avec ou sans date de naissance, au format « Prénom NOM » |
| Quelle taille de frise ? | Photos par personne : maximum, médiane, répartition |
| Les dossiers sont-ils des évènements ? | Formes réelles des chemins, précision de la date portée par le dossier |
| Peut-on se fier à la date du dossier ? | Écarts entre date du dossier et date de la photo, sur un échantillon de personnes |
| Est-ce assez rapide ? | Temps de lecture des photos d'une personne, temps et poids des vignettes |
| Peut-on recadrer la photo phare ? | Présence du cadre des visages |

### Ce que contient le rapport

Ni nom de personne, ni nom de dossier. Les personnes sont notées P1, P2… Les dossiers sont réduits à leur forme, par exemple `/synologyphotos/Pellicule/AAAA/MM/AAAA-MM-JJ texte`.

Une exception : le premier mot des dossiers d'évènement, quand il revient dans 3 dossiers au moins (mariage, anniversaire, noël…). Il sert à savoir quels types d'évènements reconnaître. Pour le retirer : `MOTS_EVENEMENTS=0`.

### Lancer la sonde (Portainer)

1. Dans Immich, créer une clé d'API **en lecture seule** : Paramètres du compte → Clés d'API. Cocher uniquement des droits de lecture (personnes, visages, photos, dossiers, albums, serveur, utilisateur). Si un droit manque, le rapport dit quelle étape a été refusée.
2. Dans les variables de la stack `homelab.yml`, ajouter `FRISE_SONDE_IMMICH_CLE` avec cette clé.
3. Créer le dossier `frise/sonde` dans le dossier docker du NAS.
4. Ajouter le service ci-dessous à `homelab.yml`, mettre à jour la stack.
5. Le conteneur s'arrête seul. Le rapport est dans `frise/sonde/rapport-sonde-frise.md` (et dans les journaux du conteneur).
6. Retirer le service de la stack et supprimer la clé d'API dans Immich.

```yaml
  frise-sonde:
    image: ghcr.io/baloodusudouest/frise:sonde
    container_name: frise_sonde
    depends_on:
      - immich-server
    environment:
      - TZ=${TZ}
      - IMMICH_URL=http://immich_server:2283
      - IMMICH_API_KEY=${FRISE_SONDE_IMMICH_CLE}   # clé en lecture seule, à supprimer après la sonde
    volumes:
      - ${DOCKER_ROOT}/frise/sonde:/data           # le rapport y est écrit
    labels:
      - "com.centurylinklabs.watchtower.enable=false"
    restart: "no"                                  # tourne une fois puis s'arrête
```

### Réglages

| Variable | Défaut | Rôle |
|---|---|---|
| `IMMICH_URL` | `http://immich_server:2283` | Adresse d'Immich vue du conteneur |
| `IMMICH_API_KEY` | (obligatoire) | Clé d'API en lecture seule |
| `PERSONNES_ECHANTILLON` | `10` | Personnes étudiées en détail (les plus photographiées et des moyennes) |
| `MAX_PHOTOS_PAR_PERSONNE` | `5000` | Plafond de photos lues par personne |
| `MOTS_EVENEMENTS` | `1` | `0` : aucun mot de dossier dans le rapport |

## Développer

```sh
pip install -r requirements-dev.txt
python -m pytest -q          # la sonde contre un faux Immich
```
