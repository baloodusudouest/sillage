"""Sillage de démonstration pour les tests d'écran : un faux Immich, une vie inventée.

    python -m tests.interface.serveur <dossier> <port>     (mot de passe : « essai-essai-essai »)"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import httpx
import uvicorn

from app import main
from app.config import Config
from app.immich import Immich
from tests.faux_immich import CAMILLE, HUGO, FauxImmich, ident, photo

MDP = "essai-essai-essai"


def dessin(nom: str) -> bytes:
    """Une image de couleur, différente pour chaque photo, pour que l'écran ressemble à quelque chose."""
    t = int(hashlib.sha1(nom.encode()).hexdigest()[:6], 16)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"><rect width="400" height="300" fill="hsl({t % 360} 35% 32%)"/>'
            f'<circle cx="{120 + t % 160}" cy="130" r="54" fill="hsl({(t + 40) % 360} 45% 62%)"/>'
            f'<rect y="220" width="400" height="80" fill="hsl({(t + 200) % 360} 30% 22%)"/></svg>').encode()


def vie() -> FauxImmich:
    faux = FauxImmich()
    serie = lambda nom, jour, n, dossier="2020/2020-01-01": [photo(f"{nom}{i}", f"{jour}T{10 + i % 10:02d}:00:00", dossier, visage=0.1 + i / 50) for i in range(n)]
    faux.photos[CAMILLE] = (
        serie("naissance", "1987-03-14", 4, "1987/1987-03-14 Naissance de Camille")
        + serie("bapteme", "1987-06-07", 9, "1987/1987-06-07 Baptême de Camille")
        + serie("jardin", "1989-08-02", 1)
        + serie("noel", "1992-12-25", 6, "1992/1992-12-25 Noël chez les grands-parents")
        + serie("plage", "1995-07-20", 12, "1995/1995-07 Vacances à la mer")
        + serie("classe", "1998-09-04", 1)
        + serie("communion", "1999-05-16", 7, "1999/1999-05-16 Communion")
        + serie("diplome", "2009-06-30", 3, "2009/2009-06-30 Remise des diplômes")
        + serie("rando", "2014-08-11", 5)
        + [dict(x, aussi=[HUGO]) for x in serie("mariage", "2019-06-15", 40)]
        + serie("anniv", "2022-03-14", 8, "2022/2022-03-14 Anniversaire 35 ans")
        + [photo("trop-tot", "1975-01-01T10:00:00")])
    faux.photos[CAMILLE][10 + 4]["type"] = "VIDEO"
    # 0.14 : des scans de Hugo, deux datés par Millésime (« vers 1978 »), un qui attend sa date (tags inventés)
    faux.photos[HUGO] = faux.photos[HUGO] + [photo("scan-a", "1978-07-01T12:00:00", "Scans/Numérisation A"),
                                             photo("scan-b", "1978-07-01T12:00:00", "Scans/Numérisation A"),
                                             photo("scan-c", "2026-01-10T10:00:00", "Scans/Numérisation A")]
    faux.tags = {"t1": ("Date estimée/1978 ±3", [ident("scan-a"), ident("scan-b")]),
                 "t2": ("Lots/Non datée", [ident("scan-c")])}
    # 0.12 : les photos du mariage forment un album (le faux Immich sert aussi /albums/{id} et ses photos)
    faux.albums = {p["id"]: "Mariage de Camille et Hugo" for p in faux.photos[CAMILLE] if "mariage" in p["originalPath"]}
    reponse = faux.repondre

    def repondre(demande: httpx.Request) -> httpx.Response:
        if demande.url.path.endswith("/thumbnail"):
            return httpx.Response(200, content=dessin(demande.url.path), headers={"content-type": "image/svg+xml"})
        return reponse(demande)
    faux.repondre = repondre
    return faux


def faux_anneau(adresse: str, jeton: str) -> dict:
    """0.16 : un faux Anneau qui garde deux sauvegardes des réglages de Sillage (aucun réseau)."""
    from urllib.parse import parse_qs, urlparse
    le = parse_qs(urlparse(adresse).query).get("le", [""])[0]
    if not le:
        return {"dates": ["2026-11-15", "2026-11-14"]}
    return {"le": le, "version": "0.16.0",
            "reglages": {"cache_mo": 300, "dossiers_muets": ["Fourre-tout"], "tag_estimee": "Date estimée",
                         "tag_non_datee": "Lots/Non datée", "hotes": []}}


def arbre_demo() -> dict:
    """0.22 : un arbre inventé d'une soixantaine de personnes autour de Camille et Hugo (faux carnet)."""
    import random
    r = random.Random(7)
    prenoms_f = ["Rose", "Jeanne", "Louise", "Alice", "Marthe", "Odile", "Clara", "Inès", "Zoé", "Lucie", "Agathe", "Margot"]
    prenoms_h = ["Jules", "Henri", "Léon", "Paul", "Émile", "Victor", "Simon", "Théo", "Basile", "Octave", "Félix", "Noël"]
    gens, liens = [], []

    def personne(nom, genre, an, mort=None, immich=None, masque=False):
        i = f"t-{len(gens)}"
        gens.append({"id": i, "nom": nom, "genre": genre, "immich": immich, "naissance": str(an) if an else "",
                     "deces": mort or "", "decede": bool(mort), "fiche": bool(immich), "carnet_uid": "demo-" + i if immich else None,
                     "personne_id": None, "masque_invites": masque})
        return i
    cam = personne("Camille ROUSSEL", "femme", "1987-03-14", immich=CAMILLE)
    hugo = personne("Hugo MARCHAND", "homme", 1985, immich=HUGO)
    liens.append({"de": cam, "vers": hugo, "type": "conjoint", "divorce": False})
    ex = personne("Anne BLANC", "femme", 1984)
    liens.append({"de": ex, "vers": hugo, "type": "conjoint", "divorce": True})

    def ascendance(enfant, nom, an, prof):
        if prof == 0:
            return
        pere = personne(f"{r.choice(prenoms_h)} {nom}", "homme", an - 28, f"{an + 40}-01-01" if an < 1960 else None)
        mere = personne(f"{r.choice(prenoms_f)} {nom}", "femme", an - 26, f"{an + 50}-06-01" if an < 1950 else None,
                        masque=(prof == 2 and nom == "MARCHAND"))
        liens.extend([{"de": pere, "vers": mere, "type": "conjoint", "divorce": False},
                      {"de": pere, "vers": enfant, "type": "parent"}, {"de": mere, "vers": enfant, "type": "parent"}])
        for _ in range(r.randint(1, 2)):
            frere = personne(f"{r.choice(prenoms_h + prenoms_f)} {nom}", r.choice(["femme", "homme"]), an + r.randint(-4, 4))
            liens.extend([{"de": pere, "vers": frere, "type": "parent"}, {"de": mere, "vers": frere, "type": "parent"}])
            if r.random() < 0.6:
                cousin = personne(f"{r.choice(prenoms_h + prenoms_f)} {nom}", r.choice(["femme", "homme"]), an + 28)
                liens.append({"de": frere, "vers": cousin, "type": "parent"})
        ascendance(pere, nom, an - 28, prof - 1)
        ascendance(mere, r.choice(["DURAND", "FABRE", "VIDAL", "MARTY"]), an - 26, prof - 1)
    ascendance(cam, "ROUSSEL", 1987, 3)
    ascendance(hugo, "MARCHAND", 1985, 2)
    for k in range(2):
        e = personne(f"{['Léa', 'Tom'][k]} MARCHAND", ["femme", "homme"][k], 2016 + k * 3)
        liens.extend([{"de": cam, "vers": e, "type": "parent"}, {"de": hugo, "vers": e, "type": "parent"}])
    return {"contrat": 1, "ok": True, "genere_le": "2026-11-27T00:00:00+01:00", "personnes": gens, "liens": liens}


def faux_carnet():
    """0.22 : carnet de démonstration : aucune fiche, l'arbre inventé, les propositions acceptées."""
    arbre = arbre_demo()

    def repondre(d: httpx.Request) -> httpx.Response:
        if d.url.path == "/sillage/arbre":
            return httpx.Response(200, json=arbre)
        if d.url.path == "/sillage/propositions":
            return httpx.Response(200, json={"ok": True, "deja": False})
        if d.url.path == "/sillage/personnes":
            return httpx.Response(200, json={"personnes": []})
        return httpx.Response(404, json={})
    return httpx.MockTransport(repondre)


def main_() -> None:
    racine, port = Path(sys.argv[1]), int(sys.argv[2])
    (racine / "data").mkdir(parents=True, exist_ok=True)
    cfg = Config(password=MDP, immich_url="http://immich", immich_cle="cle", data=racine / "data",
                 static=Path(__file__).resolve().parents[2] / "app" / "static",
                 attente_connexion=False, jeton_ha="jeton-ha", carnet_url="http://carnet", jeton="jeton-demo")
    # 0.16 : le tag des non datées est un réglage de l'écran Réglages (fichier reglages.json du dossier de données)
    import json
    reglages = racine / "data" / "reglages.json"
    if not reglages.exists():
        reglages.write_text(json.dumps({"tag_non_datee": "Lots/Non datée"}))
    main.ETAT.update(cfg=cfg, immich=Immich("http://immich", "cle", transport=vie().transport()),
                     lire_sauvegarde=faux_anneau, carnet_transport=faux_carnet())
    # 0.15 : l'adresse d'Immich pour le navigateur vient de l'annuaire de l'Anneau (faux, sans réseau)
    from app import maison
    main.ANNUAIRE = maison.Annuaire(url="http://anneau", jeton="j",
                                    lire=lambda: [{"nom": "Immich", "locale": "http://photos.exemple"},
                                                         {"nom": "Carnet", "locale": "http://carnet.exemple"},
                                                         {"nom": "Treemich", "locale": "http://arbre.exemple"}])
    # 0.5 : trois invitations de démonstration, notées dans invites.json pour les tests d'écran
    import threading
    import time
    from datetime import date, timedelta

    def inviter():
        for _ in range(100):
            try:
                if httpx.get(f"http://127.0.0.1:{port}/health").status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        fin, h = (date.today() + timedelta(days=2)).isoformat(), {"Authorization": "Bearer jeton-ha"}
        jetons = {}
        for chambre, noms in (("seule", ["Camille ROUSSEL"]), ("couple", ["Camille ROUSSEL", "Hugo MARCHAND"]), ("inconnu", ["Personne INCONNUE"])):
            r = httpx.post(f"http://127.0.0.1:{port}/ha/sejour", headers=h, json={"chambre": chambre, "noms": noms, "jusqu_au": fin, "du": fin})
            jetons[chambre] = r.json()["chemin"]
        (racine / "invites.json").write_text(json.dumps(jetons))
    threading.Thread(target=inviter, daemon=True).start()
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main_()
