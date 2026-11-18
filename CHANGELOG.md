# Journal des versions

## 0.16.4 — 18 novembre 2026 (constats moyens de l'audit)
- **M25** : « Voir l'album » de l'invité suit le même filtre que son chemin : jamais une photo archivée, masquée ou verrouillée, et à plusieurs invités jamais une photo où il y a quelqu'un d'autre que les invités et les hôtes. **Jamais essayé contre le vrai Immich.**
- **M26** : les photos lues pour chaque personne ouverte ne restent plus en mémoire pour toujours : 50 personnes au plus, la plus anciennement lue part.
- `maison.py` du socle 0.8.2 (audit M3) : réglages secrets reconnus par mots, adresse avec identifiant écartée, champ `ecartes` dans la sauvegarde (noms seulement).

## 0.16.3 — 18 novembre 2026 (cookies Secure)
- **Cookies `Secure` en https** (audit du 17/11/2026, même correctif dans toutes les applis maison) : ouverte en https (directement, derrière Tailscale Serve qui le dit par `X-Forwarded-Proto`, ou d'après l'origine de la page), l'appli pose ses cookies de session avec l'attribut `Secure` : ils ne partent jamais en clair. En http (adresse locale), rien ne change.
- `entrypoint.sh` refuse de lancer l'appli en root quand `/data` appartient à root (dossier créé par Docker) et dit le remède ; dépannage seulement : `MAISON_ROOT_ACCEPTE=oui`.

## 0.16.2 — 18 novembre 2026 (révocation du cookie commun)
- **« Se déconnecter » dans l'Anneau ferme vraiment la connexion commune** (audit du 17/11/2026, même correctif dans toutes les applis maison) : le cookie commun `maison_session` porte maintenant la génération tenue par l'Anneau (« génération.expiration.signature ») ; « Se déconnecter » l'augmente, et chaque appli la lit dans l'annuaire de l'Anneau (`/externe/services`, au plus une minute de retard) : un cookie commun d'avant la déconnexion ne vaut plus nulle part. Si l'Anneau ne répond pas, le cookie reste accepté comme avant (rien ne se bloque). **Toutes les applis doivent être à jour ensemble** ; une seule reconnexion est demandée après la mise à jour.
- Module commun `maison.py` (socle 0.8.0) : `generation_commune()`, `definir_generation_commune()` ; l'annuaire lit aussi `generation_commune` (une ancienne réponse de l'Anneau, liste seule, reste lue).

## 0.16.1 — 17 novembre 2026 (connexion plus sûre)
- **Connexion plus sûre** (audit du 17/11/2026, même correctif dans toutes les applis maison) :
  - un cookie portant un caractère non ASCII donnait une erreur 500 sur toute l'API ; il est maintenant simplement refusé ;
  - les clés qui signent les cookies (celui de l'appli et le cookie commun `maison_session` posé par l'Anneau) sont tirées du mot de passe par PBKDF2 : un cookie capté sur le réseau local ne permet plus de chercher le mot de passe à grande vitesse. **Toutes les applis doivent être à jour ensemble** ; une seule reconnexion est demandée après la mise à jour ;
  - des essais de mot de passe lancés en parallèle ne contournent plus le délai : au-delà de 30 essais en 5 minutes, tout est refusé sans comparer.
- Module commun `maison.py` (socle 0.7.0) : l'annuaire de l'Anneau est relu 30 s après un échec (avant : 10 min sans adresses après un redémarrage de la stack) ; un réglage `nan` ou infini est refusé ; un `reglages.json` abîmé est mis de côté (`.corrompu`) au lieu d'être écrasé.
- Le jeton de Home Assistant est comparé en octets (un en-tête non ASCII donnait une erreur 500).

## 0.16.0 — 16 novembre 2026
- **Les réglages d'usage quittent la stack pour l'écran Réglages** : mots des temps forts, dossiers muets, place des vignettes, tag des dates estimées, tag des scans non datés. Ils changent tout de suite, sans redémarrer (chemins et frises des chambres refaits, vignettes élaguées). Gardés dans `/data/reglages.json`.
- **Reprise une seule fois** : au premier démarrage de la 0.16, chaque réglage prend la valeur de son ancienne variable de la stack (`SILLAGE_MOTS`, `SILLAGE_DOSSIERS_MUETS`, `SILLAGE_CACHE_MO`, `SILLAGE_TAG_ESTIMEE`, `SILLAGE_TAG_NON_DATEE`) si elle est posée ; une ligne au journal du conteneur le dit. Ensuite ces variables ne sont plus lues.
- **Tag des scans non datés laissé vide** : Sillage le demande à Chambre noire (`/externe/noms`, jeton commun). Connexion dit d'où vient le tag.
- **Sauvegarde** : `GET /externe/sauvegarde` rend les réglages à l'Anneau (jeton commun seulement ; sans jeton, adresse fermée). Ni variable, ni chemin, ni secret.
- **Restaurer les réglages** (écran Réglages) : choisir une date, voir ce qui changerait (avant → sauvegardé), confirmer. Anneau injoignable ou rien à restaurer : un message clair.
- **Anciens noms retirés** : `SILLAGE_PASSWORD` (seul `MAISON_PASSWORD` compte), `SILLAGE_CARNET_JETON` (seul `MAISON_JETON` part vers carnet), `SILLAGE_IMMICH_ADRESSE` et `SILLAGE_IMMICH_PORT` (adresse d'Immich par l'Anneau, sinon même hôte, port 2283). Le jeton de Home Assistant (`SILLAGE_JETON_HA`) ne change pas.
- Tests : 57 du serveur (sans réseau : faux Anneau, faux Chambre noire), 28 d'écran (Réglages et Restaurer sur PC et iPhone).

## 0.15.0 — 16 novembre 2026
- **Variables communes de la maison** (module `app/maison.py` du socle 0.5.0, copié tel quel) :
  - mot de passe : `MAISON_PASSWORD`, repli sur `SILLAGE_PASSWORD` (toujours 12 caractères au moins) ;
  - jeton envoyé à carnet (`/sillage/personnes`) : `SILLAGE_CARNET_JETON` tant qu'il est dans la stack, puis le jeton commun `MAISON_JETON` ;
  - lien « Ouvrir dans Immich » : adresse lue dans l'Anneau (tuile « Immich », adresse privée quand Sillage est ouvert par Tailscale), puis `SILLAGE_IMMICH_ADRESSE`, puis le même hôte que Sillage avec `SILLAGE_IMMICH_PORT`, comme avant ;
  - `/ha/` garde le jeton de Home Assistant (`SILLAGE_JETON_HA`) : le jeton commun ne l'ouvre pas.
- Pas de lecture seule à régler : Sillage n'écrit chez aucun service.
- Rien ne change tant que la stack n'a pas les nouvelles variables : chaque ancien nom reste lu.
- Tests : 51 du serveur (copie du module non retouchée, mot de passe commun puis repli, jeton envoyé, porte de HA, adresse par l'annuaire puis replis), 26 d'écran.

## 0.14.1 — 15 novembre 2026
- **Plus de saisie de date de décès dans Sillage.** La date se met dans carnet ou dans Treemich, nulle part ailleurs : Sillage la lit dans carnet (qui la reçoit de Treemich, d'iCloud ou de sa fiche). Bouton « Ajouter une date de décès » et adresse `PUT /api/personne/{id}/fin` retirés. Une personne décédée d'après carnet mais sans date porte la mention « la mettre dans carnet ou dans Treemich ». Une date saisie avec la 0.14.0 n'est plus lue.
- Tests : 47 du serveur, 26 d'écran.

## 0.14.0 — 15 novembre 2026
- **Les scans datés par Millésime entrent dans le chemin, dits « vers 1975 ».** Sillage lit dans Immich les tags que Millésime pose (`Date estimée/1975 ±3`, début réglable par `SILLAGE_TAG_ESTIMEE`) : les scans d'une même année estimée font une étape, « vers 1975 », avec l'âge « vers 5 ans » et un point en pointillé sur le trait. Ils ne se mêlent pas aux vraies photos du même jour. Vaut aussi pour la page des invités et pour « Raconter » (« Vers 1975, vers 5 ans : … »).
- **Les scans qui attendent leur date restent hors du chemin**, comptés sous le chemin (« 3 scans pas encore datés ») : réglage `SILLAGE_TAG_NON_DATEE`, le tag complet des scans non datés, le même que dans Millésime. Vide : pas lu, ces scans gardent la date qu'ils ont dans Immich. Un scan estimé qui porte encore ce tag est pris comme estimé.
- **Date de décès.** Elle vient de carnet quand la fiche en a une complète (carnet 2.24.1 et suivantes) ; sinon elle se saisit sous le nom, sur le chemin (« Ajouter une date de décès », « Décès sans date : la saisir » quand carnet dit la personne décédée). Gardée dans Sillage seulement. L'âge s'arrête : la liste montre « 1932 – 2019 » ; ce qui est daté après le décès sort du chemin et est compté. « Raconter » l'écrit après la naissance.
- **Connexion** : une tuile « Scans de Millésime » (scans estimés, scans en attente, tag introuvable, droit manquant). La clé d'API de Sillage doit pouvoir lire les tags (`tag.read`) ; sans ce droit, le chemin se fait comme avant et la tuile le dit.
- Toujours rien d'écrit dans Immich ni dans carnet : les tags sont lus par une recherche.
- Jamais essayé sur la vraie installation : la lecture des tags (droit `tag.read`), le temps pris par la recherche d'un tag d'estimation par année.
- Tests : 48 du serveur, 26 d'écran.

## 0.13.0 — 14 novembre 2026
- **Frises des invités prêtes d'avance.** Dès que Home Assistant pose les invités d'une chambre (`/ha/sejour`), Sillage prépare leur frise en fond, la garde dans sa base (table `frises`) et lit d'avance les photos phares dans le cache sur disque. La page de la chambre s'affiche alors sans rien demander à Immich, même après un redémarrage.
- **Mise à jour une fois par nuit**, à 2 h (heure du conteneur, `TZ` de la stack ; réglable par `SILLAGE_HEURE_FRISES`) : les frises de toutes les invitations en cours sont refaites avec les photos ajoutées, les noms d'albums relus.
- Une correction faite par le propriétaire (photo retirée, étape masquée…) ou un changement d'hôtes refait tout de suite les frises concernées.
- Au démarrage, une invitation sans frise (base d'avant la 0.13) est préparée.
- Onglet Chambres : « Frise préparée aujourd'hui à … · refaite chaque nuit à 2 h ». `/health` donne `frises_pretes`.






## 0.12.2 — 14 novembre 2026
- **Une seule place pour fermer.** La croix de l'étape, de la photo en grand, de l'album et de la photo d'un invité est maintenant toujours au même endroit — le coin haut droit de l'écran, sous la barre d'état de l'iPhone — avec le même dessin. Une seule croix à la fois (celle de ce qui est au-dessus). « Voir tout l'album » / « Voir l'album » lui font face, en haut à gauche. Un test vérifie que les croix tombent au même pixel.
- L'album couvre entièrement ce qui est derrière (on voyait le compteur de la photo au travers) ; trois colonnes de photos sur iPhone.
## 0.12.1 — 14 novembre 2026
- **« Voir l'album » restait vide pour les invités.** Immich ne dit pas qui est sur les photos d'un album : le filtre « un invité est reconnu » ne gardait rien. Les photos de l'album sont maintenant croisées avec celles où un invité est reconnu ; et quand l'étape n'est dans aucun album (nom tiré du dossier, « Noël 2023 »), « Voir l'album » montre les photos de l'étape elle-même — celles que le compteur annonce. Le titre est alors celui de l'étape.
## 0.12.0 — 14 novembre 2026
- **Voir tout l'album d'une photo, dans Sillage.** Sur ta page, une photo ouverte en grand a un bouton « Voir tout l'album » : toutes les photos de l'album qui la contient, par date, en grille ; un toucher en ouvre une en grand (flèches, glisser, vidéos lues) ; Échap revient à la grille puis à la photo.
- **Pour les invités aussi** (carte de Home Assistant, « Ouvrir en grand ») : « Voir l'album » sur la photo en grand. L'invité ne voit que les photos de l'album **où l'un des invités est reconnu** : un album peut contenir d'autres gens et d'autres moments. Ces photos ne sont servies que par cette invitation, et seulement après l'ouverture de l'album.
- Sillage n'écrit toujours rien dans Immich (lecture des albums seulement). Une photo dans aucun album : la page le dit.
## 0.11.0 — 14 novembre 2026
- **Page d'invité à plusieurs : filtrer par personne.** Les prénoms et « Ensemble » de la légende sont maintenant des boutons : un clic ne garde que les étapes de cette personne (ou des moments ensemble), un second clic retire le filtre ; on peut en choisir deux à la fois. « Tout montrer » revient à tout. Vaut dans la carte de Home Assistant, dans « Ouvrir en grand » et dans l'onglet « Chambres ». Si le choix ne donne rien parmi les temps forts, la page le dit et propose « Voir tout ».
## 0.10.1 — 14 novembre 2026
- **Sillage passe en lavande crépuscule** (`#a98fd8`, le miel doré avant), icône comprise. L'or est gardé pour l'Anneau : carnet, Sillage et l'Anneau avaient trois ors voisins. Dans la frise de plusieurs invités, le quatrième invité prend l'ancien miel (sa lavande était trop proche des moments ensemble, qui suivent la couleur de Sillage).

## 0.10.0 — 13/11/2026

- **Noms d'étapes plus propres** (vus sur ta photothèque) : l'année en tête d'un album part (« 2007 - Soirée class » → « Soirée class »), comme pour les dossiers. Un lot de numérisation (« 1998 Numérisation … », « Scans … ») n'est plus pris pour un nom : ses scans datés au mois se réunissent par année.
- **Les vidéos se lisent** dans la photo ouverte en grand (propriétaire seulement), lues par morceaux dans Immich.
- **Les vignettes sont gardées sur le disque** de Sillage (`/data/vignettes`, 500 Mo au plus, réglable par `SILLAGE_CACHE_MO`, 0 pour couper) : une vignette déjà vue ne redemande plus Immich, même après un redémarrage. Les moins récemment servies partent en premier.
- **Tuile « À vérifier »** sur la liste : les personnes sans date de naissance dans Immich (leur chemin est rangé par année au lieu de l'âge), d'un toucher.
- Tests : 38 du serveur, 21 d'écran.

## 0.9.0 — 13/11/2026

- **Moins d'étapes, plus parlantes** (vu sur une vraie frise de 333 étapes, dont « Apéro » des dizaines de fois) :
  - les étapes du même nom à moins de deux mois d'écart n'en font qu'une, même si d'autres passent entre elles : « Apéro · 8 janvier – 5 mars 2021 · 3 fois » ;
  - les scans sans nom datés au 1er du mois se réunissent par année : « 1998 · 9 photos ».
- Partout : ton chemin et la page des invités. Nommer, masquer ou choisir la photo phare d'une étape réunie la touche toute entière.
- Tests : 34 du serveur, 18 d'écran.

## 0.8.0 — 13/11/2026

- **Page d'invité : la photo phare s'ouvre en grand** d'un clic ou d'un toucher, avec le nom et la date de l'étape ; fermeture par la croix, un clic à côté ou Échap. Seules les photos phares, comme avant : les autres photos de l'étape restent réservées au propriétaire.
- Côté Home Assistant (template `chambre_photo` v2.2) : un lien « Ouvrir en grand ↗ » sous la carte ouvre la page d'invité dans un nouvel onglet.

## 0.7.0 — 13/11/2026

- **Plusieurs invités : une seule frise en couleurs.** Les moments où ils sont ensemble (miel), et pour chacun, dans sa couleur, ses photos seul ou avec les hôtes de la maison. Une photo où il y a quelqu'un d'autre n'y entre pas. Par décennies du calendrier ; une légende (● Camille ● Hugo ● Ensemble) et le prénom sur chaque carte. Plus d'onglets « chacun son chemin ».
- **Hôtes de la maison**, réglés dans Sillage (Réglages, choisis parmi les personnes d'Immich). Sans hôte, chaque invité ne garde que ses photos seul.
- **Page d'invité sans titre** : une ligne (« Votre chemin ensemble »), la légende, la bascule, et la frise tout de suite dessous — pensé pour la carte de 300 px des chambres.
- Tests : 33 du serveur, 18 d'écran.

## 0.6.0 — 13/11/2026

- **Onglet « Chambres »** : les pages que Home Assistant a préparées pour les chambres d'amis, dès qu'un séjour y est programmé. Pour chaque chambre : les invités, les dates, les noms qu'Immich ne connaît pas, et l'aperçu de la page telle que la verra le tableau de bord de la chambre. Lecture seule : c'est Home Assistant qui crée et retire les pages.
- `POST /ha/sejour` accepte la date d'arrivée (`du`, facultative, AAAA-MM-JJ). La changer garde le même lien. Package HA `sillage_invites.yaml` v1.3.
- Tests : 33 du serveur, 18 d'écran.

## 0.5.0 — 13/11/2026

- **Vue des invités.** Une page sans mot de passe, `/invite/<jeton>`, faite pour le tableau de bord d'une chambre d'amis. Home Assistant la prépare au début du séjour : `POST /ha/sejour` (en-tête `Authorization: Bearer <SILLAGE_JETON_HA>`) avec la chambre, les noms des invités (quatre au plus) et le dernier jour. Sillage cherche chaque nom parmi les personnes nommées d'Immich (à l'identique, puis sans accents ; un homonyme n'est pas pris) et rend le chemin de la page. Le lien vaut jusqu'au lendemain du dernier jour, à midi ; un nouveau séjour dans la chambre donne un nouveau lien et efface l'ancien. Sans nom, la chambre est vidée.
- **Ce que voit l'invité** : son chemin, temps forts d'abord (bascule « Tout »), avec la photo phare de chaque étape. Ni Raconter, ni photos en grand, ni corrections, ni « Ouvrir dans Immich ». Seules les photos phares passent par le lien.
- **Plusieurs invités** : leur chemin commun (photos où ils sont ensemble), découpé par décennies (« Années 2010 »). Sans photo commune, le chemin de chacun, en onglets. Personne de trouvé, ou personne sans photo : un mot d'accueil.
- **Toujours sombre**, comme les autres applis, même sur un appareil réglé en clair.
- Tests : 32 du serveur, 16 d'écran.

## 0.4.3 — 13/11/2026

- **Un nom de dossier ne perd plus son nombre.** Sillage retirait tous les chiffres en tête du nom, pas seulement la date : « 2004-04-01 50 ans de mariage… » devenait « ans de mariage… ». Seule une vraie date est retirée maintenant (année, année-mois, année-mois-jour, jour-mois-année, ou une période de deux dates).

## 0.4.2 — 13/11/2026

- **La croix d'une photo ouverte en grand se ferme d'un clic au centre.** Le compteur (« 2 / 40 »), remonté en haut à la 0.3.0, passait par-dessus : seul le bas du bouton répondait.
- **« Ouvrir dans Immich »** devient un bouton, avec les autres gestes de la photo. Sans adresse réglée (`SILLAGE_IMMICH_ADRESSE`), le lien vise le même hôte que Sillage sur le port d'Immich (`SILLAGE_IMMICH_PORT`, en http). Ce lien est un geste du propriétaire : une future vue d'invité ne l'aura pas.

## 0.4.1 — 13/11/2026

- **Les noms des évènements sont écrits à la plume**, comme sur l'Anneau (même écriture, couleur miel), sur le chemin et en tête de l'étape ouverte. Une étape sans nom garde sa date en caractères droits.
- **Majuscule d'office** à la première lettre d'un nom, qu'il vienne d'un album, d'un dossier ou de toi ; le reste du nom n'est pas touché.

## 0.4.0 — 13/11/2026

- **Les personnes viennent de carnet.** Avec un jeton réglé (`SILLAGE_CARNET_JETON`, le même que `CARNET_JETON_SILLAGE` dans carnet 2.15), la liste d'ouverture est celle des fiches de carnet liées à une personne d'Immich, les proches d'abord, sous le nom de la fiche. Les autres personnes nommées d'Immich se trouvent par la recherche (« hors carnet »). Une fiche liée à une personne masquée dans Immich s'ouvre quand même. La date de naissance reste celle d'Immich ; une personne décédée n'affiche plus d'âge.
- **Immich en secours** : si carnet ne répond pas ou refuse le jeton, la liste est celle des personnes nommées d'Immich, et l'écran le dit.
- L'écran « Connexion » a une tuile carnet. Sillage n'écrit rien dans carnet.
- Tests : 27 du serveur, 12 d'écran.

## 0.3.0 — 13/11/2026

- **Corrections**, gardées dans Sillage (rien n'est écrit dans Immich). Sur une étape, par le crayon : la nommer, rendre le nom d'origine, la masquer. Sur une photo ouverte en grand : en faire la photo phare, la retirer du chemin, « ce n'est pas cette personne ». En bas du chemin, « Tes corrections » montre les étapes masquées et les photos mises de côté, avec « Remettre ». Les corrections sont rattachées à l'empreinte du fichier : elles survivent à la migration, qui change l'identifiant des photos.
- **Noms d'étapes.** Le nom vient de l'album le plus fréquent parmi trois photos de l'étape (la photo phare, la première, la dernière), et plus seulement de la photo phare ; une photo isolée cherche aussi son album. Un dossier qui ne dit rien (nom d'appareil, « DCIM », dossier fourre-tout) n'est plus pris pour un nom ; `SILLAGE_DOSSIERS_MUETS` allonge la liste. Une étape nommée à la main est un temps fort.
- **Raconter** : le récit du chemin, écrit par gabarit à partir des étapes visibles — une phrase par étape nommée (date, âge, nom), les autres comptées. Il se relit, se corrige, se garde et se copie ; « Repartir du chemin » le refait.
- **Le trait s'anime** : il se remplit à mesure qu'on descend, et les étapes apparaissent en entrant dans l'écran. Coupé si l'appareil demande moins d'animations.
- Les photos lues dans Immich sont gardées dix minutes : une correction recalcule le chemin sans rien relire.
- Tests : 25 du serveur, 12 d'écran.

## 0.2.0 — 13 novembre 2026
- **Connexion commune.** Connecté à l'Anneau, on n'a plus à se connecter ici : l'appli accepte le cookie « maison_session » que l'Anneau pose, quand elle est servie par la même adresse que lui. Le cookie est signé avec le mot de passe commun : une appli qui a un autre mot de passe continue de demander le sien. Il vaut trente jours, ou jusqu'au changement du mot de passe ; « Se déconnecter » le retire du navigateur.

## 0.1.0 — 13/11/2026

Première version. Liste des personnes nommées d'Immich, chemin d'une personne en étapes et chapitres d'âge, temps forts, étape ouverte avec galerie et photo en grand. Lecture seule d'Immich, images servies derrière le mot de passe.
