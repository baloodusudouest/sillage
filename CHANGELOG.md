# Journal des versions

## 0.26.6 — 27 novembre 2026 (arbre des invités : le nom de famille partout)

- **Arbre des invités : le nom de famille est toujours montré** (demande de Julien, 27/11/2026), aussi pour un mineur ou une personne sans date de naissance (avant : prénom seul). Inchangé : ni visage ni date pour eux ; une personne cochée « jamais aux invités » dans carnet reste un point sans nom. La règle de vie privée du conseil du 27/11/2026 est assouplie sur ce point par Julien.
- Tests revus. Jamais essayé sur la vraie installation.

## 0.26.5 — 27 novembre 2026 (« nouveau » = entré dans le sillage)

- **Constaté le 27/11/2026 sur la vraie installation** (essai SIL-18) : les 21 photos envoyées dans Immich ce jour-là n'avaient encore **aucun visage nommé** (reconnaissance faciale d'Immich pas encore passée) : elles n'étaient dans le sillage de personne, donc pas dans « Quoi de neuf ». Et le « J'ai vu » touché à 18:06 les aurait cachées une fois reconnues, car elles avaient été envoyées avant.
- **Correctif** : pour Julien, une photo est nouvelle quand elle **entre dans le sillage** : à la première préparation, sa date d'ajout à Immich ; ensuite, l'heure où Sillage la voit apparaître (envoyée, ou visage reconnu ou nommé plus tard dans Immich). « J'ai vu » ne cache donc plus une photo reconnue après coup. Les invités et la Gazette gardent la date d'ajout à Immich.
- Test `test_photo_entree_tard_dans_le_sillage`. Jamais essayé sur la vraie installation.

## 0.26.4 — 27 novembre 2026 (« J'ai vu » dans Quoi de neuf)

- **Bouton « J'ai vu »** en haut du bloc « Quoi de neuf » (demande de Julien, 27/11/2026) : le bloc se ferme et ce qui est déjà arrivé n'est plus montré, sur tous les appareils (`POST /api/nouveautes/vu`, réglage `nouveautes_vues_le` dans la base) ; les marques « Nouvelle » du chemin suivent. Les arrivées suivantes reviennent, sous « Quoi de neuf · depuis ta dernière lecture ».
- La date d'ajout des photos est gardée à la seconde (avant : au jour) ; un jour comme « depuis » veut dire « après ce jour ». Les sillages déjà préparés gardent leurs dates au jour jusqu'à leur prochaine préparation (au plus tard la nuit du mardi).
- Tests : `test_j_ai_vu`, test d'écran complété. Jamais essayé sur la vraie installation.

## 0.26.3 — 27 novembre 2026 (plus de pavé sur l'arbre pendant « Lien avec… »)

- **Le pavé du lien est retiré** (demande de Julien, 27/11/2026) : il cachait une grande partie de la vue. Il reste deux boutons en bas, **Voir à plat** (pas dans l'arbre à plat) et **Fermer** ; le lien se lit sur les cartes de l'arbre (« Fille de cousin »…) et reste dit au lecteur d'écran.
- **Vie 3D** : la caméra se place pour voir tout le chemin une fois le cylindre tourné (iPhone et PC).
- Tests d'écran revus. Jamais essayé sur la vraie installation.

## 0.26.2 — 27 novembre 2026 (« Lien avec… » dessiné sur le cylindre en Vie 3D)

- **Vie 3D : le chemin se dessine sur le cylindre** (demande de Julien, 27/11/2026) au lieu du schéma à plat : « Lien avec… » passe la vue en « Tout l'arbre », allume le chemin (branches et personnes, le reste en retrait), tourne le cylindre pour mettre le chemin face à l'écran et arrête la rotation lente tant que le chemin est allumé. Lien « Le voir dans l'arbre à plat ». Le schéma reste pour l'éventail. Test d'écran complété. Jamais essayé sur la vraie installation.

## 0.26.1 — 27 novembre 2026 (réglages de l'arbre cachables)

- **Arbre : cacher les réglages de la vue** (demande de Julien, 27/11/2026, sur iPhone) : toucher le titre « Arbre · L'arbre de … » replie les boutons (Vie 3D / Éventail / Arbre, Lien avec…, Liste, Proches / Tout l'arbre, Revenir à…) ; le chevron les remontre. Choix gardé sur l'appareil (`sillage-arbre-replie`). Test d'écran du propriétaire complété. Jamais essayé sur la vraie installation.

## 0.26.0 — 27 novembre 2026 (« Quoi de neuf » dans les sillages)

- **« Quoi de neuf »** (choix de Julien, 27/11/2026 ; dossier « Quoi de neuf » et conseil du même jour). Est nouveau ce qui a été **ajouté à Immich** après une date (`createdAt`, jour à l'heure du conteneur) : une étape dont toutes les photos sont nouvelles est une **nouvelle étape**, sinon **« +n photos »** ; une nouvelle photo prise avant cette date est **« retrouvée »** (scans, archives). Les 6 étapes les plus fournies sont nommées, le reste résumé (« et n photos dans m autres étapes »). Calcul à la lecture, sans historique.
- **Pour Julien** : bloc « Quoi de neuf · 30 derniers jours » en haut de la liste des sillages (personnes de carnet, sillages préparés ; `GET /api/nouveautes`). Toucher une ligne ouvre le sillage **sur l'étape** (`#/chemin/<id>/<étape>`), les photos nouvelles marquées « Nouvelle », les étapes concernées « Nouveau » (`nouvelles` dans la réponse du chemin). La date d'ajout de chaque photo est gardée avec le sillage préparé (colonne `ajouts` de `sillage_pret`).
- **Pour les invités** : « Du nouveau depuis votre dernier séjour » en haut de leur page : étapes de leur frise, photos ajoutées depuis la fin de leur séjour précédent (table `sejours` : personne, arrivée, fin ; l'invitation note `depuis`) ; rien au premier séjour. Identifiants de photos opaques comme le reste de la page ; toucher une ligne descend jusqu'à l'étape.
- **Pour la Gazette (La Récidive)** : `GET /externe/nouveautes?personne=<immich>&depuis=AAAA-MM-JJ` (jeton commun, contrat 1) : `{contrat, etapes: [{nom, annee, debut, photos, nombre, nouvelle, retrouvee}], autres_photos, autres_etapes}` ; mêmes photos que la frise d'un invité seul.
- Limites : une photo renvoyée dans Immich (réimport, migration) paraît nouvelle ; une photo dont le visage est reconnu plus tard n'est pas nouvelle (sa date d'ajout est ancienne). Jamais essayé sur la vraie installation (présence de `createdAt` dans la version d'Immich installée à vérifier).
- Tests : `tests/test_nouveautes.py` (5), deux tests d'écran.

## 0.25.1 — 27 novembre 2026 (réfection complète le mardi)

- Les sillages préparés sont **tous refaits dans la nuit du mardi** (choix de Julien, 27/11/2026) au lieu du dimanche ; les autres nuits, vérification par empreinte comme avant (`JOUR_REFECTION`). Phrase de Réglages mise à jour. Jamais essayé sur la vraie installation.

## 0.25.0 — 27 novembre 2026 (sillages préparés d'avance)

- **Les sillages des personnes de carnet sont préparés d'avance** (demande de Julien, 27/11/2026 ; dossier « Sillages préparés d'avance » et conseil du même jour) et gardés dans la base (table `sillage_pret`). Ouvrir un sillage préparé est instantané : rien n'est relu dans Immich.
- **À l'ouverture**, l'écran demande aussitôt `GET /api/chemin/{p}/verifier` : Sillage relit les photos en fond, compare l'**empreinte** (identifiant, fichier, dates, dossier, archivage, personnes reconnues de chaque photo ; pas `updatedAt`) et le **contexte** (réglages du calcul, repères de Millésime et de Chambre noire pour ses photos, corrections, version de Sillage) ; s'ils ont changé, le sillage est refait, gardé, et l'écran se met à jour (« Mis à jour avec les dernières photos »).
- **Chaque nuit** (avec les frises, `heure_frises`) : tous les sillages vérifiés ; **le dimanche, tous refaits** (un album renommé ne change pas l'empreinte). Une correction dans Sillage refait le sillage tout de suite ; un réglage du calcul changé les reprend tous en fond.
- **Au démarrage**, ceux qui manquent sont préparés en fond, une personne à la fois (pause de 0,3 s entre deux).
- **Une seule file** de préparation, sans doublon ; Immich muet : l'ancien sillage reste affiché et l'erreur est notée ; une personne sortie de carnet perd son sillage gardé (seulement si carnet a répondu).
- **Réglages › Sillages préparés** : « N sur M prêts », dernier préparé, refaits, erreurs, avancement ; bouton **Préparer les sillages maintenant** (`POST /api/sillages/preparer`, 409 si une préparation tourne). `/health` : `sillages_prets` et la tâche `preparation-sillages`.
- Les visages nommés d'Immich sans fiche carnet ne sont pas gardés (calcul à l'ouverture comme avant).
- Tests : `tests/test_sillages_prets.py` (6), test d'écran des Réglages. Jamais essayé sur la vraie installation : la durée de la vérification de nuit sur tout le carnet est inconnue.

## 0.24.0 — 27 novembre 2026 (Vie 3D d'emblée, « Tout l'arbre », arbre complet revu)

- **Trois vues** (demande de Julien, 27/11/2026) : **Vie 3D**, **Éventail**, **Arbre**. **Sablier** (trop proche de l'arbre) et **Hélice** (illisible) retirés (`lib/arbre/scene.js` supprimé).
- **L'arbre s'ouvre toujours sur la Vie 3D** (éventail si l'appareil n'a pas la 3D).
- **Vie 3D : « Proches » ou « Tout l'arbre »**. Proches : comme avant (ancêtres jusqu'aux arrière-grands-parents, conjoint, frères et sœurs, enfants, petits-enfants). Tout l'arbre : tout le monde (oncles, cousins, belle-famille…), la mise en page de l'arbre complet enroulée sur un cylindre, un étage par génération, la personne au centre face à l'écran. Choix gardé sur l'appareil (`sillage-arbre-vie-tout`).
- **Arbre complet revu** (cartes qui se chevauchaient, arbre trop étalé) : « foyers » (personne et conjoints côte à côte) placés au plus près de leurs parents puis de leurs enfants sans jamais se toucher (régression isotone), la famille de sang de la personne au centre tire plus fort que la belle-famille, quatre ordres de départ essayés et le plus serré gardé, couloirs vides refermés ; un trait par famille, barres décalées quand deux familles se recouvrent. Sur un arbre réel de 56 personnes : environ 3 000 au lieu de 4 000 de large, aucune carte superposée. Mise en page partagée : `miseEnPage(fam, c)` dans `lib/arbre/famille.js`.
- Sablier : correctif des petits-enfants superposés devenu sans objet (vue retirée).
- Interface seulement. Tests d'écran du propriétaire revus. Jamais essayé sur la vraie installation.

## 0.23.2 — 27 novembre 2026 (« Lien avec… » : on remonte par les parents)

- **Les étapes passent par les parents** (demande de Julien, 27/11/2026) : plus de « son frère » ou « sa sœur » d'un coup ; « son père Octave → sa mère Inès → sa fille Henri » quand l'arbre connaît un parent commun (la mère d'abord). Un frère ou une sœur reliés seulement par un lien « fratrie » dans Treemich restent tels quels. Le schéma montre donc le parent commun.
- Schéma : après un conjoint, la montée vers ses parents ne se décale plus d'une colonne de trop.
- Interface seulement (`lib/arbre/famille.js`, `lib/arbre/vues2d.js`). Jamais essayé sur la vraie installation.

## 0.23.1 — 27 novembre 2026 (« Lien avec… » : tout le chemin)

- **Le chemin entier, de la personne au centre jusqu'à la personne cherchée** (remarque de Julien, 27/11/2026 : on ne voyait que la montée jusqu'à l'ancêtre commun). En **éventail, sablier et arbre de vie**, « Lien avec… » ouvre un **schéma de parenté** : on remonte de la personne au centre jusqu'à l'ancêtre commun (colonne de gauche), puis on redescend jusqu'à la personne cherchée (colonne de droite) ; frère, sœur ou conjoint décalent d'une colonne ; sous chaque carte, son lien avec la personne au centre. Liens « Le voir dans l'arbre complet » et « Revenir à la vue ». Dans l'**arbre complet**, la vue se cadre sur tout le chemin ; les frères et sœurs du chemin s'allument jusqu'à leurs parents communs.
- **Chemin plus naturel** : « sa fille, puis son père » quand ce père est le conjoint devient « son conjoint » (on ne passe plus par un enfant pour rejoindre la belle-famille).
- **Liens mieux nommés** : petit-neveu, petite-nièce, arrière-grand-oncle, enfant de cousin, « cousin de la mère de Camille », et la famille de sang du conjoint « tante de Camille par alliance », « cousin … par alliance » (au lieu de « famille éloignée » ou « de la famille par alliance »).
- Interface seulement (`lib/arbre/vues2d.js` : vue `chemin`, cadrage sur le chemin ; `lib/arbre/famille.js` ; `lib/arbre/parente.js` ; `lib/Arbre.svelte`). Test d'écran du propriétaire complété (schéma en éventail). Jamais essayé sur la vraie installation.

## 0.23.0 — 27 novembre 2026 (nouvelles vues de l'arbre, « Lien avec… »)

- **Constellation retirée** (illisible selon Julien). **Cinq vues**, choisies par Julien sur deux prototypes : à plat **Éventail** (ancêtres en demi-cercles, famille proche dessous), **Sablier** (ancêtres au-dessus, enfants dessous, frères et sœurs à gauche, conjoint à droite), **Arbre** (tout l'arbre, une génération par rangée, couples reliés) ; en 3D **Vie 3D** (arbre de vie : un étage par génération nommé « ↑ Parents », « ↓ Enfants »…, rotation autour de l'axe vertical seulement, sève lumineuse qui descend des parents vers les enfants, lien écrit sur chaque carte) et **Hélice** (gardée pour l'instant). Éventail par défaut ; dernière vue gardée sur l'appareil. Les vues à plat marchent sans WebGL.
- **Toucher une personne** la met au centre et ouvre sa carte ; « Revenir à … » ramène la personne de départ.
- **« Lien avec… »** (propriétaire et invités ; un invité ne choisit que parmi les personnes qu'il voit) : le lien en clair (« Léa MARCHAND : fille de Hugo »), les étapes (« Hugo → sa fille Léa ») et le chemin qui s'allume sur l'arbre, le reste estompé ; par le sang d'abord, sinon par les couples (« par alliance ») ; « Voir dans l'arbre complet » si une partie du chemin n'est pas dans la vue.
- `lib/arbre/famille.js` (famille, `chemin`, `motEtape`, `surlignage`), `lib/arbre/vues2d.js` (vues à plat en SVG, glisser, pincer, molette), `lib/arbre/vie.js` (arbre de vie, three.js), `lib/arbre/scene.js` (hélice seule, `surligner`). Serveur inchangé. Tests d'écran `test_022_*` revus. Jamais essayé sur la vraie installation.

## 0.22.0 — 27 novembre 2026 (arbre de famille en 3D)

- **Arbre de famille** (demande de Julien du 27/11/2026, grill, conseil et prototype mesuré sur iPhone : 60 i/s à 400 personnes) : bouton « Arbre » sur le chemin d'une personne qui a au moins un lien dans Treemich ; tout l'arbre relié, en **constellation** ou en **hélice** (ancêtres en haut), bascule animée, dernière vue gardée sur l'appareil, rotation lente au repos (coupée si l'appareil réduit les animations), visages lointains en points lumineux, décédés en noir et blanc, ex-conjoints en pointillé, liste des personnes avec recherche, liste de secours sans WebGL. Couleurs : lavande et argent (l'or reste à l'Anneau).
- **Carte d'une personne** : lien de parenté en clair (« Grand-mère de Camille »), dates ; propriétaire : « Voir son sillage », « Ouvrir dans carnet » ou « Ouvrir dans Treemich ».
- **Invités** : bouton « Votre arbre de famille » sur leur page ; un seul arbre pour la chambre, invités mis en avant, légende par prénom. Règle du conseil appliquée côté serveur (vivants : année de naissance ; mineurs et âge inconnu : prénom seul, sans visage ; case « jamais aux invités » de carnet : point sans nom ; né il y a plus de 100 ans sans décès : considéré décédé). Identifiants opaques, comme pour les photos.
- **Propositions des invités** : date, nom, lien ou personne manquante, avec un mot, 20 par invitation ; table `proposition`, envoi à carnet 3.6 (`POST /sillage/propositions`), renvoi si carnet est muet, effacées 90 jours après l'envoi.
- `app/arbre.py` (parties reliées, générations, statuts) ; `frontend/src/lib/Arbre.svelte`, `lib/arbre/scene.js` (three.js 0.170.0, morceau chargé à l'ouverture), `lib/arbre/parente.js`. Le faux carnet de démonstration rend l'arbre (tests d'écran). Tests : `tests/test_arbre.py`, `test_022_*` (écran). Il faut carnet 3.6. Jamais essayé sur la vraie installation.

## 0.21.3 — 23 novembre 2026 (listes déroulantes lisibles en sombre)

- **Listes déroulantes illisibles sur PC** (constaté par Julien dans Dîme, 23/11/2026) : la liste ouverte d'un `<select>` gardait un fond blanc tout en reprenant le texte crème de l'appli. `frontend/src/app.css` reprend le bloc du socle 0.12.2 (« Listes déroulantes (socle 0.12.2) ») : choix aux couleurs des menus, titres de groupe en gras, choix désactivés en gris.
- Jamais essayé sur la vraie installation.

## 0.21.2 — 22 novembre 2026 (barre d'onglets collée en bas)
- **iPhone : barre d'onglets collée au bord bas**, sur toute la largeur, au lieu de la pilule flottante (demande de Julien, 22/11/2026, pour toutes les applis maison ; socle 0.12.1). Le rail des PC ne change pas.
- **Jamais essayé sur la vraie installation.**

## 0.21.1 — 20 novembre 2026 (socle 0.11.1)
- Copies communes du socle 0.11.1 : sur une fiche « Connexion », le titre devient « Pour le relier » quand le réglage se fait dans Réglages de l'appli (et non dans la stack).
- **Jamais essayé sur la vraie installation.**

## 0.21.0 — 20 novembre 2026 (fiches « Connexion » communes, contrat 3)
- L'écran « Connexion » passe à l'écran commun des applis maison (socle 0.11.0, `$lib/services/`) : quatre services, donc des tuiles à voyant ; la fiche s'ouvre au toucher (Ce qui est lu, Ce qui est écrit, Pour le relier, Vérifier). « Vérifier » ne teste que son service et l'âge du dernier essai est affiché ; l'ouverture de l'écran ne lance plus aucune lecture.
- Fiches : **Immich** (lit la version), **carnet** (relit la liste des fiches liées), **Scans de Millésime** (lit la liste des tags d'Immich ; les nombres de scans « vers … » et en attente sont ceux du dernier calcul du chemin), **Chambre noire** (relit le tag des scans non datés ; fiche à part, elle n'était qu'une ligne sous Millésime). Textes « lit » et « écrit » repris de l'ancien écran. Aucun geste : Sillage ne fait que lire.
- Serveur : registre `SERVICES` (`maison.Services`), `GET /api/maison/services` et `POST /api/maison/services/{id}/verifier` (session ou `ANNEAU_CLE`, au plus un essai toutes les 30 s par service, rien d'écrit). La fiche « État » de l'Anneau les lit.
- `maison.py` du socle 0.11.0 (contrat 3). Nouvelle variable facultative `ANNEAU_CLE` (compose, `.env.example`).
- L'ancienne route `GET /api/services` reste telle quelle en 0.21.0 (plus lue par l'interface) : **à retirer à la version suivante (0.22.0)**. `pages/Services.svelte` est retiré.
- Tests : 84 du serveur (`tests/test_fiches_connexion.py`, 6 nouveaux ; version du socle 0.11.0 dans `tests/test_sante.py`), 26 d'écran (le parcours de Connexion passe par les tuiles et « Vérifier »).
- **Jamais essayé sur la vraie installation.**

## 0.20.0 — 18 novembre 2026 (étapes d'une personne pour la Gazette)
- **`GET /externe/personnes/{immich_id}/etapes`** (jeton commun, contrat 1) pour la fiche complète d'une personne dans la Gazette : `{"contrat": 1, "etapes": [{"nom", "annee", "photos"}]}`. Les étapes du chemin de cette personne, mêmes règles que le chemin (photos visibles seulement, corrections de Julien comprises), sans les étapes masquées ni celles sans nom ; les plus fournies d'abord, 60 au plus. Personne inconnue : liste vide (code 200). Rien n'est écrit, ni dans Immich ni dans la base.
- Le calcul du chemin est mis à part (`_calcul_du_chemin`) pour servir à l'écran et à cette adresse ; l'écran ne change pas.
- Jamais essayé sur la vraie installation (ni la lecture par la Gazette 0.23, ni le temps de calcul d'un long chemin appelé de l'extérieur).
- Tests : 78 du serveur (5 nouveaux, `tests/test_etapes_externes.py`).

## 0.19.0 — 18 novembre 2026 (Raconter retiré)
- **« Raconter » retiré** (choix de Julien du 18/11/2026, après l'essai des IA du PC sur un chemin : aucun modèle ne tient « rien d'inventé », et le gabarit n'apporte pas assez). Plus de page Récit ni de bouton « Raconter » sur le chemin ; `GET` et `PUT /api/recit/{personne}` répondent 404 ; module `app/recit.py` supprimé (rien d'autre ne s'en servait).
- **Plus de marque « à revoir »** : un avis d'invité accepté ou corrigé dans Millésime ferme l'avis, sans lire la photo dans Immich (`GET /assets/{id}` n'est plus demandé) ni toucher aux récits.
- La page de l'invité n'a jamais montré de récit : rien à retirer de ce côté (un test le vérifie).
- **Base** : la table `recits` des bases existantes reste en place (textes de Julien), elle n'est plus ni lue ni écrite ; une base neuve ne la crée plus. Aucune migration destructive.
- Tests : 73 du serveur (3 nouveaux, 3 retirés) ; un test d'écran retiré (« Raconter »).

## 0.18.0 — 18 novembre 2026 (santé des tâches de fond)
- **Tâches suivies dans `/health`** (champ `taches`, socle 0.9.1) : `frises-de-nuit` (régulière, 86 400 s : mise à jour de nuit des frises des invités, à `SILLAGE_HEURE_FRISES`), `preparation-frises` (à la demande : préparation d'une frise d'invitation, un tour par invitation), `copie-des-bases` (régulière, 86 400 s). Une boucle de nuit ratée passe « en retard » ; une frise ratée passe la préparation en « erreur ». Le comportement de l'appli ne change pas (les erreurs restent notées au journal comme avant).
- **Copie de la base** chaque nuit à **01:30, heure de Paris** : `sillage.db` copiée de façon cohérente (API de sauvegarde de SQLite, vérifiée) vers `/data/copies/sillage-derniere.db`, écrasée chaque nuit (Hyper Backup tient l'historique) ; état dans `/health` (`copie_base`).
- `/health` : champs ajoutés `version_socle`, `taches`, `copie_base` ; rien d'existant ne change. Les messages d'erreur des tâches n'y sont qu'avec le jeton commun (`Authorization: Bearer MAISON_JETON`) ou une session valide.
- `maison.py` du socle 0.9.0. Un seul worker uvicorn (registre en mémoire).
- Jamais essayé sur la vraie installation (ni la copie de nuit, ni sa remise en place).
- Tests : 73 du serveur (3 nouveaux).

## 0.17.0 — 18 novembre 2026 (dates signalées par les invités)
- **« Pas la bonne année ? »** sous chaque photo de la page de l'invité (chemin et « Voir l'album ») : « Vers quelle année ? », case « environ », souvenir facultatif (120 caractères, texte brut). Après l'envoi : « Merci, c'est transmis à Julien », marque « signalé » et « Changer d'avis » tant que ce n'est pas traité ; écarté : « Julien a regardé, la date reste » pendant 30 jours ; merci « Grâce à vous, N photos ont retrouvé leur année ».
- **« Aidez-moi à dater »** en bas de la page de l'invité : jusqu'à 12 photos où un invité figure, hors du chemin faute de date (tag des scans non datés sans estimation), sauf celles que Julien a écartées.
- Base : table `signalement` (un avis en attente par invitation et par photo, renvoyer remplace) ; 100 avis en attente par invitation au plus (429) ; avis traités effacés après 90 jours (démarrage et nuit). Les prénoms de l'invitation sont gardés dans l'avis : une invitation expirée garde ses avis jusqu'à leur traitement.
- **Contrat 1 avec Millésime** (jeton commun) : `GET /externe/signalements` (avis en attente, avec l'identifiant Immich et la date que l'invité voyait) et `POST /externe/signalements/traite` (ferme tous les avis de la photo, rejouable). Sillage n'écrit toujours rien dans Immich.
- **Identifiants de photos propres à Sillage côté invité** (HMAC court par invitation et photo) : l'identifiant Immich ne sort plus vers l'invité, ni dans les réponses ni dans les adresses. Les adresses de vignettes des invités changent (`/api/invite/<jeton>/vignette/<id opaque>`) ; l'ancienne forme par identifiant Immich répond 404. Les frises préparées avant la 0.17 sont refaites au démarrage.
- « Raconter » : un récit gardé est marqué « à revoir » quand un avis d'une photo de la personne est accepté ou corrigé dans Millésime ; garder le texte efface la marque.
- Jamais essayé sur la vraie installation (ni la page de l'invité sur iPhone, ni la lecture par Millésime, ni la lecture des personnes d'une photo par `GET /assets/{id}` d'Immich).
- Tests : 70 du serveur (10 nouveaux).

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
