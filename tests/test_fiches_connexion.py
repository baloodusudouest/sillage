"""Fiches « Connexion » communes (contrat 3, socle 0.11.0) : forme de /api/maison/services, accès par session ou
ANNEAU_CLE seulement (jamais MAISON_JETON), « Vérifier » d'un service pas relié n'essaie rien, copies non retouchées
du module commun et de l'interface commune."""
from pathlib import Path

import pytest

from app import main, maison
from app.config import APPLI
from tests.test_api import MDP, monde  # noqa: F401 — fixture du faux Immich (Sillage n'a pas de conftest)


@pytest.fixture
def client(monde):  # noqa: F811
    c, _ = monde
    return c


def connecter(c):
    assert c.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200

RACINE = Path(__file__).resolve().parent.parent
CLE = "cle-anneau-de-test-1234567890"
IDS = ["immich", "carnet", "millesime", "chambre-noire"]
CHAMPS = {"id", "nom", "genre", "cible", "etat", "lit", "ecrit", "reglage", "detail", "verifie_le", "guide",
          "derniere_ecriture", "gestes"}


def test_forme_du_contrat_3(client):
    connecter(client)
    r = client.get("/api/maison/services")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    corps = r.json()
    assert corps["contrat"] == 3 and corps["appli"] == APPLI and corps["simule"] is False
    assert [s["id"] for s in corps["services"]] == IDS
    for s in corps["services"]:
        assert set(s) == CHAMPS and s["lit"] and s["ecrit"] and s["etat"] in maison.ETATS_SERVICE
        assert len(s["gestes"]) <= 1
        if s["etat"] == "pas_relie":
            assert s["reglage"]


def test_acces_session_ou_cle_anneau(client, monkeypatch):
    assert client.get("/api/maison/services").status_code == 401
    monkeypatch.setenv("MAISON_JETON", "jeton-commun-de-test-12345")
    entete = {"Authorization": "Bearer jeton-commun-de-test-12345"}
    assert client.get("/api/maison/services", headers=entete).status_code == 401
    monkeypatch.setenv("ANNEAU_CLE", CLE)
    assert client.get("/api/maison/services", headers={"Authorization": f"Bearer {CLE}"}).status_code == 200
    assert client.get("/api/maison/services", headers={"Authorization": "Bearer mauvaise"}).status_code == 401


def test_verifier_inconnu_et_pas_relie(client):
    connecter(client)
    assert client.post("/api/maison/services/inconnu/verifier").status_code == 404
    for s in client.get("/api/maison/services").json()["services"]:
        if s["etat"] == "pas_relie":
            apres = client.post(f"/api/maison/services/{s['id']}/verifier").json()
            assert apres["etat"] == "pas_relie" and apres["verifie_le"] is None


def test_copies_communes_non_retouchees():
    assert maison.CONTRAT == 3 and maison.VERSION_SOCLE == "0.11.1"
    assert maison.empreinte_calculee() == maison.empreinte_ecrite()
    for nom in maison.FICHIERS_INTERFACE:
        ecrite, calculee = maison.empreinte_interface(RACINE / "frontend" / "src" / "lib" / "services" / nom)
        assert ecrite and ecrite == calculee, nom


def test_verifier_immich_ne_fait_que_lire(monde):
    """Sillage 0.21 : « Vérifier » d'Immich lit la version (une demande GET), rien d'autre ; le GET de la liste
    ne lance aucun essai."""
    c, faux = monde
    connecter(c)
    faux.demandes.clear()
    assert c.get("/api/maison/services").json()["services"][0]["etat"] == "relie"
    assert faux.demandes == []
    fiche = c.post("/api/maison/services/immich/verifier").json()
    assert fiche["etat"] == "repond" and fiche["detail"].startswith("Répond, version 3.4.1.") and fiche["verifie_le"]
    assert len(faux.demandes) == 1 and faux.demandes[0][0] == "GET" and faux.demandes[0][1].endswith("/server/version")


def test_verifier_les_scans_de_millesime(monde):
    """Sillage 0.21 : la fiche « Scans de Millésime » lit la liste des tags ; tag des non datées introuvable : ne répond pas."""
    c, faux = monde
    connecter(c)
    fiche = c.post("/api/maison/services/millesime/verifier").json()
    assert fiche["etat"] == "repond" and fiche["genre"] == "maison" and fiche["cible"] == "millesime"
    assert all(m == "GET" for m, _ in faux.demandes)
    c2 = c.put("/api/reglages", json={"tag_non_datee": "Lots/Absent"})
    assert c2.status_code == 200
    main.SERVICES._dernier.clear()                    # passer la limite des 30 s
    fiche = c.post("/api/maison/services/millesime/verifier").json()
    assert fiche["etat"] == "ne_repond_pas" and "introuvable" in fiche["detail"]
