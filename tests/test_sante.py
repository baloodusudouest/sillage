"""0.18 : santé des tâches de fond et copie de la base dans /health (socle 0.9.0)."""
from __future__ import annotations

import asyncio
import time

from app import main, maison

from .test_api import MDP, monde  # noqa: F401 (fixture)


def _sante(client, **kw):
    """/health, en laissant à la boucle de copie le temps de lire son état de départ (tâche lancée au démarrage)."""
    for _ in range(50):
        j = client.get("/health", **kw).json()
        if j["copie_base"] and j["copie_base"]["bases"] == ["sillage.db"]:
            return j
        time.sleep(0.02)
    return j


def test_health_porte_la_sante_des_taches_et_la_copie(monde, monkeypatch):  # noqa: F811
    client, _ = monde
    monkeypatch.setenv("MAISON_JETON", "jeton-commun-essai")
    j = _sante(client)
    assert j["ok"] is True and j["version"] == main.__version__ and "frises_pretes" in j      # rien d'existant ne change
    assert j["version_socle"] == "0.11.1"
    taches = {t["nom"]: t for t in j["taches"]}
    assert {"frises-de-nuit", "preparation-frises", "copie-des-bases"} <= set(taches)
    assert taches["frises-de-nuit"]["type"] == "reguliere" and taches["frises-de-nuit"]["periode_s"] == 86400
    assert taches["preparation-frises"]["type"] == "demande"
    assert taches["copie-des-bases"]["periode_s"] == 86400
    assert j["copie_base"]["bases"] == ["sillage.db"] and j["copie_base"]["le"] is None   # pas encore de nuit
    assert all("message" not in t for t in j["taches"])                                  # sans jeton : pas de message
    avec = client.get("/health", headers={"Authorization": "Bearer jeton-commun-essai"}).json()
    assert all("message" in t for t in avec["taches"])
    faux = client.get("/health", headers={"Authorization": "Bearer mauvais-jeton"}).json()
    assert all("message" not in t for t in faux["taches"])
    assert client.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200
    assert all("message" in t for t in client.get("/health").json()["taches"])         # session valide


def test_un_tour_de_nuit_rate_met_la_tache_en_retard(monkeypatch):
    taches = maison.Taches()
    monkeypatch.setattr(maison, "TACHES", taches)
    taches.declarer("frises-de-nuit", periode_s=86400)
    monkeypatch.setitem(main.ETAT, "cfg", type("Cfg", (), {"heure_frises": 2})())
    monkeypatch.setattr(main, "_prochaine", lambda heure, maintenant: maintenant)     # la nuit, tout de suite

    def rate():
        raise RuntimeError("Immich muet sur http://lea:secret@immich.exemple")
    monkeypatch.setattr(main, "_rafraichir_tout", rate)

    async def un_moment():
        boucle = asyncio.create_task(main._chaque_nuit())
        while taches.etat()[0]["derniere_erreur"] is None:
            await asyncio.sleep(0.01)
        boucle.cancel()
    asyncio.run(asyncio.wait_for(un_moment(), 5))
    etat = taches.etat(avec_messages=True)[0]
    assert etat["etat"] == "en_retard" and etat["derniere_reussite"] is None
    assert "RuntimeError" in etat["message"] and "secret" not in etat["message"]


def test_une_frise_ratee_passe_la_preparation_en_erreur(monkeypatch):
    taches = maison.Taches()
    monkeypatch.setattr(maison, "TACHES", taches)
    taches.declarer("preparation-frises", type="demande")

    def rate(jeton, refaire=True):
        raise RuntimeError("Immich muet")
    monkeypatch.setattr(main, "_preparer_un", rate)
    main._preparer(["invitation-inventee"])            # l'erreur reste avalée comme avant
    assert taches.etat()[0]["etat"] == "erreur"
