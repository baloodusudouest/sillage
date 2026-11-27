"""0.22 : l'arbre de famille (vue 3D) — pour le propriétaire, pour les invités (masquage côté serveur), et les
propositions des invités envoyées à carnet. Personnes, dates et identifiants inventés."""
from __future__ import annotations

import dataclasses
import json
from datetime import date

import httpx
import pytest

from app import arbre as A
from app import main

from .faux_immich import CACHEE, CAMILLE, HUGO, ident
from .test_api import _attendre_le_fond, avec_jeton_ha, c, monde, sejour  # noqa: F401 (fixtures)

LEA = ident("lea")
AN = date.today().year


def _arbre():
    p = lambda i, nom, **k: {"id": i, "nom": nom, "genre": k.pop("genre", ""), "immich": k.pop("immich", None),  # noqa: E731
                             "naissance": k.pop("naissance", ""), "deces": k.pop("deces", ""),
                             "decede": bool(k.get("deces_flag")), "fiche": True, "carnet_uid": "uid-" + i,
                             "personne_id": "p-" + i, "masque_invites": k.pop("masque", False)}
    personnes = [
        p("t-cam", "Camille ROUSSEL", genre="femme", immich=CAMILLE, naissance="1987-03-14"),
        p("t-hugo", "Hugo MARCHAND", genre="homme", immich=HUGO, naissance="1985"),
        p("t-lea", "Léa MARCHAND", genre="femme", immich=LEA, naissance=f"{AN - 9}-05-01"),
        p("t-mamie", "Rose ROUSSEL", genre="femme", naissance="1930-01-01", deces="2010-02-02"),
        p("t-aieul", "Jules ROUSSEL", genre="homme", naissance="1890"),
        p("t-cousin", "Paul ROUSSEL", genre="homme"),
        p("t-cache", "Tante CACHÉE", genre="femme", immich=CACHEE, naissance="1960", masque=True),
        p("t-ex", "Anne BLANC", genre="femme", naissance="1984"),
        p("t-seul", "Isolé SANSLIEN"),
        p("t-autre", "Autre FAMILLE"), p("t-autre2", "Autre FAMILLE 2"),
    ]
    for x in personnes:
        x["decede"] = bool(x["deces"])
    liens = [{"de": "t-cam", "vers": "t-hugo", "type": "conjoint", "divorce": False},
             {"de": "t-cam", "vers": "t-lea", "type": "parent"}, {"de": "t-hugo", "vers": "t-lea", "type": "parent"},
             {"de": "t-mamie", "vers": "t-cam", "type": "parent"}, {"de": "t-aieul", "vers": "t-mamie", "type": "parent"},
             {"de": "t-mamie", "vers": "t-cousin", "type": "parent"}, {"de": "t-cache", "vers": "t-mamie", "type": "fratrie"},
             {"de": "t-ex", "vers": "t-hugo", "type": "conjoint", "divorce": True},
             {"de": "t-autre", "vers": "t-autre2", "type": "fratrie"}]
    return {"contrat": 1, "ok": True, "genere_le": "2026-11-27T01:00:00+01:00", "personnes": personnes, "liens": liens}


class FauxCarnet:
    def __init__(self):
        self.arbre = _arbre()
        self.recues: list[dict] = []
        self.muet = False
        self.refuse = False
        self.vues: list[tuple[str, str, str]] = []

    def __call__(self, d: httpx.Request) -> httpx.Response:
        self.vues.append((d.method, d.url.path, d.headers.get("authorization")))
        if self.muet:
            raise httpx.ConnectError("muet")
        if d.headers.get("authorization") != "Bearer jeton-commun":
            return httpx.Response(401, json={})
        if d.url.path == "/sillage/arbre":
            return httpx.Response(200, json=self.arbre)
        if d.url.path == "/sillage/propositions":
            if self.refuse:
                return httpx.Response(400, json={"detail": "refusée"})
            self.recues.append(json.loads(d.content))
            return httpx.Response(200, json={"ok": True, "deja": False})
        if d.url.path == "/sillage/personnes":
            return httpx.Response(200, json={"personnes": []})
        return httpx.Response(404)


@pytest.fixture
def carnet(monde):
    faux = FauxCarnet()
    main.ETAT["cfg"] = dataclasses.replace(main.ETAT["cfg"], carnet_url="http://carnet", jeton="jeton-commun")
    main.ETAT["carnet_transport"] = httpx.MockTransport(faux)
    main.ETAT["personnes"] = None
    return faux


# ================================================================ calculs

def test_relies_generations_et_statuts():
    g = _arbre()
    ids = A.relies(g, ["t-cam"])
    assert ids == {"t-cam", "t-hugo", "t-lea", "t-mamie", "t-aieul", "t-cousin", "t-cache", "t-ex"}
    rangs = A.generations(ids, g["liens"], "t-cam")
    assert rangs["t-aieul"] == 0 and rangs["t-mamie"] == rangs["t-cache"] == 1
    assert rangs["t-cam"] == rangs["t-hugo"] == rangs["t-cousin"] == rangs["t-ex"] == 2 and rangs["t-lea"] == 3
    jour = date(2026, 11, 27)
    assert A.statut({"deces": "inconnue"}, jour) == "decede"
    assert A.statut({"naissance": "1900"}, jour) == "decede"            # plus de 100 ans, sans décès connu
    assert A.statut({"naissance": "2010-01-01"}, jour) == "mineur"
    assert A.statut({"naissance": "1987"}, jour) == "vivant"
    assert A.statut({}, jour) == "inconnu"
    # Une boucle (Treemich mal rempli) ne fait pas tourner en rond
    boucle = [{"de": "a", "vers": "b", "type": "parent"}, {"de": "b", "vers": "a", "type": "parent"}]
    assert set(A.generations({"a", "b"}, boucle, "a")) == {"a", "b"}


# ================================================================ propriétaire

def test_arbre_du_proprietaire(c, carnet):
    r = c.get(f"/api/arbre/{CAMILLE}")
    assert r.status_code == 200, r.text
    a = r.json()["arbre"]
    assert a["depart"] == "t-cam"
    par = {p["id"]: p for p in a["personnes"]}
    assert set(par) == {"t-cam", "t-hugo", "t-lea", "t-mamie", "t-aieul", "t-cousin", "t-cache", "t-ex"}
    assert par["t-mamie"]["deces"] == "2010-02-02" and par["t-cache"]["masque_invites"] is True
    assert par["t-cam"]["visage"] == CAMILLE and par["t-cam"]["sillage"] == CAMILLE and par["t-lea"]["sillage"] is None
    assert par["t-cam"]["carnet_uid"] == "uid-t-cam"
    assert {(l["de"], l["vers"]) for l in a["liens"]} >= {("t-cam", "t-hugo"), ("t-ex", "t-hugo")}
    assert not any("t-autre" in (l["de"], l["vers"]) for l in a["liens"])
    # Les visages de cet arbre seulement
    assert c.get(f"/api/arbre/vignette/{HUGO}").status_code == 200
    assert c.get(f"/api/arbre/vignette/{ident('personne')}").status_code == 404
    # Gardé dix minutes : une seule lecture de carnet
    c.get(f"/api/arbre/{HUGO}")
    assert sum(1 for v in carnet.vues if v[1] == "/sillage/arbre") == 1


def test_sans_lien_pas_d_arbre_et_carnet_absent(c, carnet, monde):
    carnet.arbre["personnes"].append({"id": "t-x", "nom": "X", "immich": ident("x"), "liens": []})
    assert c.get(f"/api/arbre/{ident('x')}").json() == {"arbre": None}
    assert c.get(f"/api/arbre/{ident('personne')}").json() == {"arbre": None}
    main.ETAT["arbre"] = None
    carnet.muet = True
    r = c.get(f"/api/arbre/{CAMILLE}")
    assert r.status_code == 503 and "carnet" in r.json()["detail"]
    main.ETAT["cfg"] = dataclasses.replace(main.ETAT["cfg"], jeton="")
    assert c.get(f"/api/arbre/{CAMILLE}").status_code == 503
    client, _ = monde
    client.cookies.clear()
    assert client.get(f"/api/arbre/{CAMILLE}").status_code == 401


# ================================================================ invités

def _inviter(client, noms=("Camille ROUSSEL",)):
    jeton = sejour(client, avec_jeton_ha(), noms=list(noms), du=date.today().isoformat())["chemin"].split("/")[-1]
    _attendre_le_fond()
    return jeton


def test_arbre_des_invites_masque_cote_serveur(monde, carnet):
    client, _ = monde
    jeton = _inviter(client)
    r = client.get(f"/api/invite/{jeton}/arbre")
    assert r.status_code == 200, r.text
    texte = r.text
    for secret in ("t-cam", "t-mamie", "uid-", "p-t-", CAMILLE, HUGO, LEA, CACHEE, "Tante", "CACHÉE"):
        assert secret not in texte, secret
    a = r.json()["arbre"]
    par = {p["statut"] + ":" + p["nom"]: p for p in a["personnes"]}
    cam = par["vivant:Camille ROUSSEL"]
    assert cam["invite"] and cam["naissance"] == "1987" and cam["visage"] and a["depart"] == cam["id"]
    assert par["vivant:Hugo MARCHAND"]["naissance"] == "1985"
    lea = par["mineur:Léa MARCHAND"]                       # 0.26.6 : nom de famille aussi
    assert lea["naissance"] == "" and lea["visage"] is False
    mamie = par["decede:Rose ROUSSEL"]
    assert mamie["naissance"] == "1930-01-01" and mamie["deces"] == "2010-02-02" and mamie["decede"]
    assert par["decede:Jules ROUSSEL"]["naissance"] == "1890"           # né il y a plus de 100 ans
    assert par["inconnu:Paul ROUSSEL"]["naissance"] == "" and not par["inconnu:Paul ROUSSEL"]["visage"]
    masque = par["masque:"]
    assert masque["genre"] == "" and not masque["visage"] and masque["naissance"] == ""
    assert a["invites"] == [{"id": cam["id"], "prenom": "Camille"}]
    assert next(l for l in a["liens"] if l.get("divorce"))["type"] == "conjoint"
    assert r.json()["propositions_restantes"] == 20
    # Visages : seulement ceux qu'il a le droit de voir
    assert client.get(f"/api/invite/{jeton}/arbre/vignette/{cam['id']}").status_code == 200
    assert client.get(f"/api/invite/{jeton}/arbre/vignette/{lea['id']}").status_code == 404
    assert client.get(f"/api/invite/{jeton}/arbre/vignette/{CAMILLE}").status_code == 404
    assert client.get(f"/api/invite/autre-jeton/arbre").status_code == 404


def test_deux_invites_un_seul_arbre(monde, carnet):
    client, _ = monde
    jeton = _inviter(client, ("Camille ROUSSEL", "Hugo MARCHAND"))
    a = client.get(f"/api/invite/{jeton}/arbre").json()["arbre"]
    assert [i["prenom"] for i in a["invites"]] == ["Camille", "Hugo"]
    assert sum(1 for p in a["personnes"] if p["invite"]) == 2


def test_invite_hors_de_l_arbre(monde, carnet):
    client, _ = monde
    carnet.arbre["liens"] = [l for l in carnet.arbre["liens"] if "t-cam" not in (l["de"], l["vers"])]
    jeton = _inviter(client)
    assert client.get(f"/api/invite/{jeton}/arbre").json() == {"arbre": None}


def test_propositions_envoyees_a_carnet(monde, carnet):
    client, _ = monde
    jeton = _inviter(client)
    a = client.get(f"/api/invite/{jeton}/arbre").json()["arbre"]
    par = {p["nom"]: p for p in a["personnes"]}
    url = f"/api/invite/{jeton}/arbre/proposition"
    r = client.post(url, json={"personne": par["Rose ROUSSEL"]["id"], "type": "date", "champ": "naissance",
                               "valeur": "1930-01-04", "mot": "  née\nun samedi "})
    assert r.status_code == 200, r.text
    assert r.json()["propositions_restantes"] == 19
    envoi = carnet.recues[-1]
    assert envoi["personne"] == "t-mamie" and envoi["nom"] == "Rose ROUSSEL" and envoi["valeur"] == "1930-01-04"
    assert envoi["mot"] == "née un samedi" and envoi["invites"] == ["Camille"] and envoi["sejour"]["du"] == date.today().isoformat()
    # Un lien manquant vers une autre personne de l'arbre (vrais noms côté carnet seulement)
    client.post(url, json={"personne": par["Léa MARCHAND"]["id"], "type": "lien", "lien": "parent", "autre": par["Hugo MARCHAND"]["id"],
                           "mot": "Hugo est son père"})
    assert carnet.recues[-1]["autre"] == "t-hugo" and carnet.recues[-1]["nom"] == "Léa MARCHAND"
    # Refus
    for mauvais in ({"personne": "000000000000000000000000", "type": "date", "champ": "naissance", "valeur": "1930"},
                    {"personne": par["Léa MARCHAND"]["id"], "type": "date", "champ": "naissance", "valeur": "le 4"},
                    {"personne": par["Léa MARCHAND"]["id"], "type": "nom", "champ": "prenom", "valeur": ""},
                    {"personne": par["Léa MARCHAND"]["id"], "type": "lien", "lien": "cousin", "mot": "x"},
                    {"personne": par["Léa MARCHAND"]["id"], "type": "personne", "mot": ""}):
        assert client.post(url, json=mauvais).status_code in (404, 422), mauvais


def test_carnet_muet_la_proposition_attend_puis_part(monde, carnet):
    client, _ = monde
    jeton = _inviter(client)
    a = client.get(f"/api/invite/{jeton}/arbre").json()["arbre"]
    cam = next(p for p in a["personnes"] if p["invite"])
    carnet.muet = True
    r = client.post(f"/api/invite/{jeton}/arbre/proposition", json={"personne": cam["id"], "type": "nom", "champ": "nom",
                                                                    "valeur": "ROUSSEL-MARCHAND"})
    assert r.status_code == 200 and not carnet.recues
    assert len(main.ETAT["base"].propositions_a_envoyer()) == 1
    carnet.muet = False
    assert main._envoyer_propositions() == 1 and carnet.recues[0]["valeur"] == "ROUSSEL-MARCHAND"
    assert main.ETAT["base"].propositions_a_envoyer() == []
    # Refusée par carnet : marquée, plus renvoyée
    carnet.refuse = True
    client.post(f"/api/invite/{jeton}/arbre/proposition", json={"personne": cam["id"], "type": "personne", "mot": "Il manque Tom"})
    assert main.ETAT["base"].propositions_a_envoyer() == []


def test_plafond_par_invitation(monde, carnet, monkeypatch):
    client, _ = monde
    monkeypatch.setattr(main, "PROPOSITIONS_MAX", 2)
    jeton = _inviter(client)
    cam = next(p for p in client.get(f"/api/invite/{jeton}/arbre").json()["arbre"]["personnes"] if p["invite"])
    corps = {"personne": cam["id"], "type": "personne", "mot": "Il manque Tom"}
    url = f"/api/invite/{jeton}/arbre/proposition"
    assert client.post(url, json=corps).status_code == 200
    assert client.post(url, json=corps).status_code == 200
    assert client.post(url, json=corps).status_code == 429


def test_invitation_expiree_plus_d_arbre(monde, carnet):
    client, _ = monde
    jeton = _inviter(client)
    _attendre_le_fond()
    with main.ETAT["base"]._c:
        main.ETAT["base"]._c.execute("UPDATE invites SET expire = '2000-01-01T12:00:00'")
    assert client.get(f"/api/invite/{jeton}/arbre").status_code == 404
    assert client.post(f"/api/invite/{jeton}/arbre/proposition", json={}).status_code == 404
