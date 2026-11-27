"""La mémoire de Sillage : les corrections faites à la main, les invitations et les avis des invités. Un petit fichier SQLite.

Une correction est rattachée à l'empreinte du fichier, pas à l'identifiant de la photo dans Immich :
l'identifiant change quand la photo est renvoyée (migration), l'empreinte non."""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

SORTES = ("pas_elle", "retiree", "phare", "titre", "masquee")
ISSUES = ("acceptee", "corrigee", "ecartee")     # 0.17 : ce que Millésime a fait d'un avis d'invité


def maintenant_tz() -> str:
    """0.17 : l'heure du conteneur avec son décalage (« 2026-11-18T10:00:00+01:00 »), comme le contrat avec Millésime."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def quand_tz(texte: str) -> datetime:
    """Relit une heure gardée ; sans décalage, c'est l'heure du conteneur."""
    d = datetime.fromisoformat(texte)
    return d if d.tzinfo else d.astimezone()


class Base:
    def __init__(self, chemin: Path):
        self._verrou = threading.Lock()
        self._c = sqlite3.connect(chemin, check_same_thread=False)
        self._c.row_factory = sqlite3.Row
        self._c.executescript("""
            CREATE TABLE IF NOT EXISTS marques (personne TEXT NOT NULL, empreinte TEXT NOT NULL, sorte TEXT NOT NULL,
                                               valeur TEXT NOT NULL DEFAULT '', le TEXT NOT NULL,
                                               PRIMARY KEY (personne, empreinte, sorte));
            -- 0.19 : « Raconter » retiré. La table « recits » des bases existantes reste en place (textes de l'utilisateur),
            -- elle n'est plus ni lue ni écrite, ni créée dans une base neuve.
            CREATE TABLE IF NOT EXISTS reglages (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS invites (jeton TEXT PRIMARY KEY, chambre TEXT NOT NULL, personnes TEXT NOT NULL,
                                                expire TEXT NOT NULL, cree_le TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS frises (jeton TEXT PRIMARY KEY, contenu TEXT NOT NULL, le TEXT NOT NULL);
            -- 0.17 : dates signalées par les invités. Les prénoms et les personnes de l'invitation sont recopiés dans l'avis :
            -- une invitation expirée ou retirée disparaît de « invites », ses avis restent jusqu'à leur traitement.
            CREATE TABLE IF NOT EXISTS signalement (id TEXT PRIMARY KEY, jeton TEXT NOT NULL, asset TEXT NOT NULL,
                                                    annee INTEGER NOT NULL, environ INTEGER NOT NULL DEFAULT 0,
                                                    mot TEXT NOT NULL DEFAULT '', date_affichee TEXT, invites TEXT NOT NULL,
                                                    personnes TEXT NOT NULL DEFAULT '[]', le TEXT NOT NULL,
                                                    traite_le TEXT, issue TEXT);
            CREATE UNIQUE INDEX IF NOT EXISTS signalement_actif ON signalement (jeton, asset) WHERE traite_le IS NULL;
            CREATE INDEX IF NOT EXISTS signalement_asset ON signalement (asset);
            -- 0.22 : corrections proposées par les invités depuis l'arbre, envoyées à carnet (« À traiter »).
            -- `corps` est déjà la forme reçue par carnet (identifiants de Treemich), pour pouvoir renvoyer plus tard.
            CREATE TABLE IF NOT EXISTS proposition (id TEXT PRIMARY KEY, jeton TEXT NOT NULL, corps TEXT NOT NULL,
                                                    le TEXT NOT NULL, envoyee_le TEXT, etat TEXT NOT NULL DEFAULT 'attente');
            CREATE INDEX IF NOT EXISTS proposition_jeton ON proposition (jeton);
        """)
        # 0.6 : date d'arrivée, pour l'onglet « Chambres » (bases de la 0.5 : colonne ajoutée)
        if "du" not in [l["name"] for l in self._c.execute("PRAGMA table_info(invites)")]:
            self._c.execute("ALTER TABLE invites ADD COLUMN du TEXT NOT NULL DEFAULT ''")
            self._c.commit()

    def fermer(self) -> None:
        self._c.close()

    def marques(self, personne: str) -> dict[str, dict[str, str]]:
        """empreinte → {sorte: valeur} pour une personne."""
        sortie: dict[str, dict[str, str]] = {}
        with self._verrou:
            for l in self._c.execute("SELECT empreinte, sorte, valeur FROM marques WHERE personne = ?", (personne,)):
                sortie.setdefault(l["empreinte"], {})[l["sorte"]] = l["valeur"]
        return sortie

    def marquer(self, personne: str, sorte: str, effacer: list[str], poser: str | None, valeur: str = "") -> None:
        """Retire la marque de ces empreintes, puis la pose sur une seule (ou sur aucune)."""
        with self._verrou, self._c:
            self._c.executemany("DELETE FROM marques WHERE personne = ? AND empreinte = ? AND sorte = ?",
                                [(personne, e, sorte) for e in effacer])
            if poser:
                self._c.execute("INSERT OR REPLACE INTO marques VALUES (?, ?, ?, ?, ?)",
                                (personne, poser, sorte, valeur, datetime.now().isoformat(timespec="seconds")))

    # ------------------------------------------------------------ 0.5 : invités des chambres
    def invite(self, jeton: str) -> dict | None:
        """L'invitation de ce jeton, si elle n'a pas expiré : {chambre, personnes: [{id, nom}], expire}."""
        with self._verrou:
            l = self._c.execute("SELECT * FROM invites WHERE jeton = ? AND expire > ?",
                                (jeton, datetime.now().isoformat(timespec="seconds"))).fetchone()
        return ({"chambre": l["chambre"], "personnes": json.loads(l["personnes"]), "expire": l["expire"], "du": l["du"]}
                if l else None)

    def poser_invite(self, chambre: str, personnes: list[dict], expire: str, du: str = "") -> str:
        """Une invitation par chambre : la même si rien n'a changé, sinon une nouvelle (l'ancienne ne marche plus).
        La date d'arrivée ne compte pas : la changer garde le lien."""
        corps = json.dumps(personnes, ensure_ascii=False, sort_keys=True)
        maintenant = datetime.now().isoformat(timespec="seconds")
        with self._verrou, self._c:
            self._c.execute("DELETE FROM invites WHERE expire <= ?", (maintenant,))
            l = self._c.execute("SELECT jeton FROM invites WHERE chambre = ? AND personnes = ? AND expire = ?",
                                (chambre, corps, expire)).fetchone()
            if l:
                self._c.execute("UPDATE invites SET du = ? WHERE jeton = ?", (du, l["jeton"]))
                return l["jeton"]
            self._c.execute("DELETE FROM invites WHERE chambre = ?", (chambre,))
            jeton = secrets.token_urlsafe(24)
            self._c.execute("INSERT INTO invites (jeton, chambre, personnes, expire, cree_le, du) VALUES (?, ?, ?, ?, ?, ?)",
                            (jeton, chambre, corps, expire, maintenant, du))
            self._c.execute("DELETE FROM frises WHERE jeton NOT IN (SELECT jeton FROM invites)")
            return jeton

    def reglage(self, cle: str, defaut=None):
        """0.7 : un réglage fait dans l'appli (valeur JSON)."""
        with self._verrou:
            l = self._c.execute("SELECT valeur FROM reglages WHERE cle = ?", (cle,)).fetchone()
        return json.loads(l["valeur"]) if l else defaut

    def poser_reglage(self, cle: str, valeur) -> None:
        with self._verrou, self._c:
            self._c.execute("INSERT INTO reglages VALUES (?, ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
                            (cle, json.dumps(valeur, ensure_ascii=False)))

    def invitations(self) -> list[dict]:
        """Les invitations encore valables, par date d'arrivée : {jeton, chambre, personnes, expire, du}."""
        with self._verrou:
            lignes = self._c.execute("SELECT * FROM invites WHERE expire > ? ORDER BY du, chambre",
                                     (datetime.now().isoformat(timespec="seconds"),)).fetchall()
        return [{"jeton": l["jeton"], "chambre": l["chambre"], "personnes": json.loads(l["personnes"]),
                 "expire": l["expire"], "du": l["du"]} for l in lignes]

    def retirer_invites(self, chambre: str) -> None:
        with self._verrou, self._c:
            self._c.execute("DELETE FROM invites WHERE chambre = ?", (chambre,))
            self._c.execute("DELETE FROM frises WHERE jeton NOT IN (SELECT jeton FROM invites)")

    # ------------------------------------------------------------ 0.13 : frises des invités préparées d'avance
    def frise(self, jeton: str) -> tuple[dict, str] | None:
        """La frise déjà préparée pour cette invitation, et sa date de préparation."""
        with self._verrou:
            l = self._c.execute("SELECT contenu, le FROM frises WHERE jeton = ?", (jeton,)).fetchone()
        return (json.loads(l["contenu"]), l["le"]) if l else None

    def garder_frise(self, jeton: str, contenu: dict) -> str:
        le = datetime.now().isoformat(timespec="seconds")
        with self._verrou, self._c:
            if self._c.execute("SELECT 1 FROM invites WHERE jeton = ?", (jeton,)).fetchone():   # pas pour une invitation retirée entre-temps
                self._c.execute("INSERT OR REPLACE INTO frises VALUES (?, ?, ?)",
                                (jeton, json.dumps(contenu, ensure_ascii=False), le))
            self._c.execute("DELETE FROM frises WHERE jeton NOT IN (SELECT jeton FROM invites)")
        return le

    def oublier_frises(self, jetons: list[str]) -> None:
        with self._verrou, self._c:
            self._c.executemany("DELETE FROM frises WHERE jeton = ?", [(j,) for j in jetons])

    def preparees(self) -> dict[str, str]:
        """jeton → date de préparation, pour les invitations encore valables."""
        with self._verrou:
            return {l["jeton"]: l["le"] for l in self._c.execute(
                "SELECT f.jeton, f.le FROM frises f JOIN invites i ON i.jeton = f.jeton WHERE i.expire > ?",
                (datetime.now().isoformat(timespec="seconds"),))}

    # ------------------------------------------------------------ 0.17 : dates signalées par les invités
    def signaler(self, jeton: str, asset: str, annee: int, environ: bool, mot: str, date_affichee: str | None,
                 invites: list[str], personnes: list[str], limite: int) -> dict | None:
        """Pose l'avis de cette invitation sur cette photo. Un seul avis en attente par (invitation, photo) : renvoyer
        remplace (nouvel identifiant). Rend None si l'invitation a déjà `limite` avis en attente (sans compter celui
        qu'on remplace)."""
        with self._verrou, self._c:
            actif = self._c.execute("SELECT id FROM signalement WHERE jeton = ? AND asset = ? AND traite_le IS NULL",
                                    (jeton, asset)).fetchone()
            if not actif and self._c.execute("SELECT COUNT(*) FROM signalement WHERE jeton = ? AND traite_le IS NULL",
                                             (jeton,)).fetchone()[0] >= limite:
                return None
            if actif:
                self._c.execute("DELETE FROM signalement WHERE id = ?", (actif["id"],))
            ligne = {"id": secrets.token_urlsafe(12), "jeton": jeton, "asset": asset, "annee": int(annee),
                     "environ": 1 if environ else 0, "mot": mot, "date_affichee": date_affichee,
                     "invites": json.dumps(invites, ensure_ascii=False), "personnes": json.dumps(personnes),
                     "le": maintenant_tz()}
            self._c.execute("INSERT INTO signalement (id, jeton, asset, annee, environ, mot, date_affichee, invites, personnes, le) "
                            "VALUES (:id, :jeton, :asset, :annee, :environ, :mot, :date_affichee, :invites, :personnes, :le)", ligne)
        return ligne

    def retirer_signalement(self, jeton: str, asset: str) -> int:
        """Changer d'avis : l'avis en attente de cette invitation sur cette photo disparaît (un avis traité reste)."""
        with self._verrou, self._c:
            return self._c.execute("DELETE FROM signalement WHERE jeton = ? AND asset = ? AND traite_le IS NULL",
                                   (jeton, asset)).rowcount

    @staticmethod
    def _avis(l: sqlite3.Row) -> dict:
        return {"id": l["id"], "jeton": l["jeton"], "asset": l["asset"], "annee": l["annee"], "environ": bool(l["environ"]),
                "mot": l["mot"], "date_affichee": l["date_affichee"], "invites": json.loads(l["invites"]),
                "personnes": json.loads(l["personnes"]), "le": l["le"], "traite_le": l["traite_le"], "issue": l["issue"]}

    def signalements_de(self, jeton: str) -> list[dict]:
        """Tous les avis d'une invitation (en attente et traités), du plus ancien au plus récent."""
        with self._verrou:
            return [self._avis(l) for l in self._c.execute("SELECT * FROM signalement WHERE jeton = ? ORDER BY le, rowid", (jeton,))]

    def signalements_en_attente(self) -> list[dict]:
        """Les avis pas encore traités, toutes invitations (expirées comprises), du plus ancien au plus récent."""
        with self._verrou:
            return [self._avis(l) for l in self._c.execute("SELECT * FROM signalement WHERE traite_le IS NULL ORDER BY le, rowid")]

    def traiter(self, asset: str, issue: str) -> tuple[int, list[str]]:
        """Ferme tous les avis en attente de cette photo (toutes invitations). Rejouable : la deuxième fois, rien à fermer.
        Rend le nombre d'avis fermés et les personnes des invitations concernées."""
        if issue not in ISSUES:
            raise ValueError(issue)
        with self._verrou, self._c:
            lignes = self._c.execute("SELECT personnes FROM signalement WHERE asset = ? AND traite_le IS NULL", (asset,)).fetchall()
            self._c.execute("UPDATE signalement SET traite_le = ?, issue = ? WHERE asset = ? AND traite_le IS NULL",
                            (maintenant_tz(), issue, asset))
        return len(lignes), list(dict.fromkeys(p for l in lignes for p in json.loads(l["personnes"])))

    def effacer_traites(self, jours: int = 90, maintenant: datetime | None = None) -> int:
        """Les avis traités depuis plus de `jours` jours sont effacés. Rend le nombre d'avis effacés."""
        limite = (maintenant or datetime.now().astimezone()) - timedelta(days=jours)
        with self._verrou, self._c:
            vieux = [(l["id"],) for l in self._c.execute("SELECT id, traite_le FROM signalement WHERE traite_le IS NOT NULL")
                     if quand_tz(l["traite_le"]) <= limite]
            self._c.executemany("DELETE FROM signalement WHERE id = ?", vieux)
        return len(vieux)

    # ------------------------------------------------------------ 0.22 : propositions des invités sur l'arbre
    def proposer(self, jeton: str, corps: dict, limite: int) -> str | None:
        """Garde une proposition ; None si l'invitation en a déjà `limite`."""
        with self._verrou, self._c:
            n = self._c.execute("SELECT COUNT(*) FROM proposition WHERE jeton = ?", (jeton,)).fetchone()[0]
            if n >= limite:
                return None
            ident = corps["id"]
            self._c.execute("INSERT INTO proposition(id, jeton, corps, le) VALUES (?, ?, ?, ?)",
                            (ident, jeton, json.dumps(corps, ensure_ascii=False), maintenant_tz()))
        return ident

    def propositions_de(self, jeton: str) -> int:
        with self._verrou:
            return self._c.execute("SELECT COUNT(*) FROM proposition WHERE jeton = ?", (jeton,)).fetchone()[0]

    def propositions_a_envoyer(self) -> list[dict]:
        with self._verrou:
            return [{"id": l["id"], "corps": json.loads(l["corps"])}
                    for l in self._c.execute("SELECT id, corps FROM proposition WHERE etat = 'attente' ORDER BY le")]

    def proposition_envoyee(self, ident: str, etat: str = "envoyee") -> None:
        with self._verrou, self._c:
            self._c.execute("UPDATE proposition SET etat = ?, envoyee_le = ? WHERE id = ?", (etat, maintenant_tz(), ident))

    def effacer_propositions(self, jours: int = 90) -> int:
        """Les propositions envoyées (ou refusées par carnet) depuis plus de `jours` jours sont effacées."""
        limite = (datetime.now().astimezone() - timedelta(days=jours)).isoformat(timespec="seconds")
        with self._verrou, self._c:
            return self._c.execute("DELETE FROM proposition WHERE etat != 'attente' AND envoyee_le < ?", (limite,)).rowcount
