"""0.25 : sillages des personnes de carnet préparés d'avance, vérifiés à l'ouverture et chaque nuit (personnes inventées)."""
import time

from app import main

from .faux_immich import CAMILLE, HUGO, photo
from .test_api import avec_carnet, c, monde  # noqa: F401 (fixtures)


def _carnet():
    """Camille est dans carnet ; Hugo n'est qu'un visage nommé d'Immich."""
    return avec_carnet((200, {"personnes": [
        {"carnet_id": "f1", "nom": "Camille R.", "immich_id": CAMILLE, "groupes": [], "proche": True, "decede": False}]}))


def _finir():
    """Attend la fin de la préparation en fond (et des fils qu'elle lance)."""
    for _ in range(500):
        vivants = [f for f in main.ETAT["fond"] if f.is_alive()]
        if not vivants and not main.ETAT["prep"]["en_cours"] and not main.ETAT["file_sillages"]:
            return
        for f in vivants:
            f.join(timeout=0.05)
        time.sleep(0.01)
    raise AssertionError("préparation trop longue")


def _lectures(faux, qui):
    return sum(1 for m, chemin in faux.demandes if chemin == "/search/metadata")


def test_preparation_puis_ouverture_sans_relire_immich(monde, monkeypatch):
    client, faux = monde
    monkeypatch.setattr(main, "PAUSE_SILLAGES", 0)
    assert client.post("/api/connexion", json={"mot_de_passe": main.ETAT["cfg"].password}).status_code == 200
    _carnet()
    assert client.post("/api/sillages/preparer").json() == {"ok": True}
    _finir()
    etat = client.get("/api/sillages").json()
    assert etat["prets"] == 1 and etat["carnet"] == 1 and etat["preparation"]["refaits"] == 1
    assert main.ETAT["base"].sillages_prets().keys() == {CAMILLE}                 # Hugo (hors carnet) n'est pas gardé
    assert client.get("/health").json()["sillages_prets"] == 1
    main.ETAT["lues"].clear()
    avant = len(faux.demandes)
    r = client.get(f"/api/chemin/{CAMILLE}").json()
    assert r["pret"] and r["personne"]["nom"] == "Camille R."
    assert not any(ch == "/search/metadata" for _, ch in faux.demandes[avant:])    # rien relu : instantané
    # vérification : rien n'a changé
    assert client.get(f"/api/chemin/{CAMILLE}/verifier").json() == {"pareil": True}


def test_verifier_refait_quand_une_photo_arrive(monde, monkeypatch):
    client, faux = monde
    monkeypatch.setattr(main, "PAUSE_SILLAGES", 0)
    assert client.post("/api/connexion", json={"mot_de_passe": main.ETAT["cfg"].password}).status_code == 200
    _carnet()
    client.post("/api/sillages/preparer")
    _finir()
    photos_avant = client.get(f"/api/chemin/{CAMILLE}").json()["photos"]
    faux.photos[CAMILLE].append(photo("anniversaire", "2021-04-02T10:00:00", "2021/2021-04-02 Anniversaire"))
    r = client.get(f"/api/chemin/{CAMILLE}/verifier").json()
    assert r["mis_a_jour"] is True and r["photos"] == photos_avant + 1
    assert client.get(f"/api/chemin/{CAMILLE}").json()["photos"] == photos_avant + 1   # gardé pour la prochaine fois
    # date corrigée dans Immich : refait aussi
    faux.photos[CAMILLE][-1]["localDateTime"] = "2021-05-02T10:00:00.000Z"
    assert client.get(f"/api/chemin/{CAMILLE}/verifier").json().get("mis_a_jour") is True
    # Immich ne change que updatedAt (vignette refaite) : rien n'est refait
    faux.photos[CAMILLE][-1]["updatedAt"] = "2026-11-27T03:00:00.000Z"
    assert client.get(f"/api/chemin/{CAMILLE}/verifier").json() == {"pareil": True}


def test_reglage_et_correction_refont_le_sillage(monde, monkeypatch):
    client, faux = monde
    monkeypatch.setattr(main, "PAUSE_SILLAGES", 0)
    assert client.post("/api/connexion", json={"mot_de_passe": main.ETAT["cfg"].password}).status_code == 200
    _carnet()
    client.post("/api/sillages/preparer")
    _finir()
    le = main.ETAT["base"].sillage_pret(CAMILLE)["le"]
    contexte = main.ETAT["base"].sillage_pret(CAMILLE)["contexte"]
    # un réglage du calcul change : les sillages sont repris en fond, le contexte change
    assert client.put("/api/reglages", json={"dossiers_muets": ["Divers"]}).status_code == 200
    _finir()
    assert main.ETAT["base"].sillage_pret(CAMILLE)["contexte"] != contexte
    # une correction faite dans Sillage : refait tout de suite
    ch = client.get(f"/api/chemin/{CAMILLE}").json()
    etape = ch["chapitres"][0]["etapes"][0]
    r = client.post(f"/api/chemin/{CAMILLE}/marque", json={"sorte": "titre", "poser": etape["phare"], "valeur": "Nommée"})
    assert r.status_code == 200, r.text
    assert any(e["nom"] == "Nommée" for chap in r.json()["chapitres"] for e in chap["etapes"])
    gardee = main.ETAT["base"].sillage_pret(CAMILLE)["contenu"]
    assert any(e["nom"] == "Nommée" for chap in gardee["chapitres"] for e in chap["etapes"])
    assert le is not None


def test_immich_muet_l_ancien_sillage_reste(monde, monkeypatch):
    client, faux = monde
    monkeypatch.setattr(main, "PAUSE_SILLAGES", 0)
    assert client.post("/api/connexion", json={"mot_de_passe": main.ETAT["cfg"].password}).status_code == 200
    _carnet()
    client.post("/api/sillages/preparer")
    _finir()
    faux.refuse = 500
    main.ETAT["personnes"] = (time.monotonic(), main.ETAT["personnes"][1])          # la liste reste connue
    main._demander([CAMILLE], forcer=True, par="essai")
    _finir()
    pret = main.ETAT["base"].sillage_pret(CAMILLE)
    assert pret["erreur"] and pret["contenu"]["photos"] > 0                          # l'ancien reste, l'erreur est notée
    assert client.get("/api/sillages").json()["en_erreur"] == 1
    faux.refuse = 0
    assert client.get(f"/api/chemin/{CAMILLE}").json()["pret"]                         # toujours affiché
    main._demander([CAMILLE], par="essai")
    _finir()
    assert not main.ETAT["base"].sillage_pret(CAMILLE)["erreur"]                       # réussi : l'erreur s'efface


def test_une_seule_file_et_personne_sortie_de_carnet(monde, monkeypatch):
    client, faux = monde
    monkeypatch.setattr(main, "PAUSE_SILLAGES", 0.05)
    assert client.post("/api/connexion", json={"mot_de_passe": main.ETAT["cfg"].password}).status_code == 200
    _carnet()
    client.post("/api/sillages/preparer")
    assert client.post("/api/sillages/preparer").status_code in (200, 409)          # pas deux préparations
    _finir()
    assert main.ETAT["prep"]["total"] == 1
    # Camille sort de carnet : son sillage préparé est retiré à la préparation suivante
    avec_carnet((200, {"personnes": []}))
    main._tout_preparer(par="essai")
    _finir()
    assert main.ETAT["base"].sillages_prets() == {}
    assert HUGO not in main.ETAT["base"].sillages_prets()


def test_demarrage_prepare_les_manquants(monde, monkeypatch):
    client, faux = monde
    monkeypatch.setattr(main, "PAUSE_SILLAGES", 0)
    _carnet()
    assert main._tout_preparer(manquants=True, par="demarrage") == 1
    _finir()
    assert main._tout_preparer(manquants=True, par="demarrage") == 0                 # déjà prêt : rien à faire


def test_refection_complete_le_mardi(monde, monkeypatch):
    """0.25.1 : chaque nuit, vérification ; la nuit du mardi, tous refaits (choix de Julien)."""
    import datetime as dt
    appels = []
    monkeypatch.setattr(main, "_tout_preparer", lambda forcer=False, manquants=False, par="": appels.append((forcer, par)) or 0)
    monkeypatch.setattr(main, "_preparer", lambda jetons: None)
    for jour, attendu in ((dt.datetime(2026, 12, 1, 2, 0), True), (dt.datetime(2026, 11, 29, 2, 0), False)):   # mardi, dimanche
        class Fige(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return jour
        monkeypatch.setattr(main, "datetime", Fige)
        main._rafraichir_tout()
        assert appels[-1] == (attendu, "nuit")
