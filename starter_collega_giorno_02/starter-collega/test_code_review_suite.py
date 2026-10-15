"""Test deterministici dell'involucro della Code Review Suite (senza rete, senza modello).

Verificano i sei invarianti dell'involucro: budget, concorrenza, limiti di tempo,
non-mutazione, formato e routing. Non testano il giudizio del modello (non deterministico):
testano cio' che invece deve esserlo.

    python test_code_review_suite.py
"""

import asyncio
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import code_review_suite as s  # noqa: E402


class TestFormato(unittest.TestCase):
    """Invariante 5: parsing robusto delle uscite dei reviewer."""

    def test_array_pulito(self):
        f, ok = s.leggi_findings('[{"file":"A.java","riga":3,"gravita":"HIGH",'
                                 '"descrizione":"x","correzione_proposta":"y"}]', "r")
        self.assertTrue(ok)
        self.assertEqual((f[0]["file"], f[0]["riga"], f[0]["gravita"]), ("A.java", 3, "HIGH"))

    def test_array_vuoto_e_nessun_rilievo(self):
        f, ok = s.leggi_findings("[]", "r")
        self.assertTrue(ok)
        self.assertEqual(f, [])

    def test_wrapper(self):
        f, ok = s.leggi_findings('bla {"findings":[{"file":"A.java","riga":1,'
                                 '"gravita":"LOW"}]} bla', "r")
        self.assertTrue(ok)
        self.assertEqual(f[0]["gravita"], "LOW")

    def test_chiavi_corrotte_della_skill(self):
        f, ok = s.leggi_findings('[{"ile":"A.java","iga":9,"gravita":"CRITICAL"}]', "r")
        self.assertTrue(ok)
        self.assertEqual((f[0]["file"], f[0]["riga"]), ("A.java", 9))

    def test_prosa_con_parentesi_attenzione(self):
        testo = 'Vedi [questo link](x) e poi:\n[{"file":"A.java","riga":2,"gravita":"HIGH"}]'
        f, ok = s.leggi_findings(testo, "r")
        self.assertTrue(ok)
        self.assertEqual(f[0]["riga"], 2)

    def test_array_di_non_oggetti_non_e_nessun_rilievo(self):
        _, ok = s.leggi_findings('["solo testo"]', "r")
        self.assertFalse(ok)

    def test_gravita_sconosciuta_non_declassa(self):
        f, _ = s.leggi_findings('[{"file":"A.java","riga":1,"gravita":"CRITICA"}]', "r")
        self.assertEqual(f[0]["gravita"], "UNKNOWN")
        self.assertGreater(s.RANGO["UNKNOWN"], s.RANGO["HIGH"])

    def test_nessun_json(self):
        _, ok = s.leggi_findings("nessun json qui", "r")
        self.assertFalse(ok)


class TestBudget(unittest.TestCase):
    """Invariante 1: tetto di spesa che interrompe davvero."""

    def test_superato_per_token(self):
        b = s.Budget(cap_token=100, secondi=1000)
        b.aggiungi(99, 0)
        self.assertFalse(b.superato())
        b.aggiungi(1, 0)
        self.assertTrue(b.superato())

    def test_superato_per_costo(self):
        b = s.Budget(cap_token=10**9, secondi=1000, cap_costo=1.0)
        b.aggiungi(0, 1.0)
        self.assertTrue(b.superato())

    def test_superato_per_tempo(self):
        b = s.Budget(cap_token=10**9, secondi=-1)
        self.assertTrue(b.superato())


class TestRiconciliazione(unittest.TestCase):
    """Gravita' di gate = massima; divergenza conservata; dedup."""

    def _esito(self, nome, findings):
        return s.Esito(reviewer=nome, stato="OK", findings=findings)

    def test_conflitto_max_e_conservato(self):
        a = {"file": "A.java", "riga": 5, "gravita": "HIGH",
             "descrizione": "N+1 query: accountRepo.findById eseguita una volta per ogni movimento nel ciclo",
             "correzione_proposta": "p", "reviewer": "movement-domain-reviewer"}
        b = {"file": "A.java", "riga": 5, "gravita": "LOW",
             "descrizione": "N+1 query: accountRepo.findById eseguito per ogni movimento dentro il ciclo",
             "correzione_proposta": "p", "reviewer": "performance-reviewer"}
        r = s.riconcilia([self._esito("movement-domain-reviewer", [a]),
                          self._esito("performance-reviewer", [b])])
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["gravita"], "HIGH")
        self.assertTrue(r[0]["conflitto"])
        self.assertEqual(r[0]["gravita_per_lente"],
                         {"movement-domain-reviewer": "HIGH", "performance-reviewer": "LOW"})

    def test_findings_diversi_non_si_accorpano(self):
        a = {"file": "A.java", "riga": 5, "gravita": "HIGH",
             "descrizione": "manca idempotenza sul trasferimento", "correzione_proposta": "p",
             "reviewer": "r1"}
        b = {"file": "A.java", "riga": 5, "gravita": "HIGH",
             "descrizione": "audit trail assente per importi oltre soglia", "correzione_proposta": "p",
             "reviewer": "r2"}
        self.assertEqual(len(s.riconcilia([self._esito("r1", [a]), self._esito("r2", [b])])), 2)


class TestNonMutazioneERouting(unittest.TestCase):
    """Invarianti 4 e 6: preflight edit: deny e dotazione dei reviewer."""

    def test_reviewer_senza_edit_deny_rifiutato(self):
        motivo = s.controlla_sola_lettura(s.REPO_ROOT, "compliance-amount-reviewer")
        self.assertIsNone(motivo)

    def test_reviewer_inesistente_rifiutato(self):
        self.assertIsNotNone(s.controlla_sola_lettura(s.REPO_ROOT, "non-esiste-reviewer"))

    def test_tutti_i_reviewer_dichiarano_edit_deny(self):
        for r in s.REVIEWERS:
            with self.subTest(reviewer=r):
                self.assertIsNone(s.controlla_sola_lettura(s.REPO_ROOT, r))

    def test_reviewer_nel_perimetro(self):
        self.assertEqual(len(s.REVIEWERS), 4)
        self.assertEqual(len(set(s.REVIEWERS)), 4)


class TestConcorrenzaETempi(unittest.TestCase):
    """Invarianti 2 e 3: partenza simultanea e tetto di tempo complessivo."""

    def test_partenza_simultanea_con_fake(self):
        # Sostituisce esegui() con un finto che dorme: i quattro devono avanzare insieme.
        originali = s.esegui

        async def finto(reviewer, target, budget, tetto):
            inizio = time.perf_counter()
            await asyncio.sleep(0.3)
            e = s.Esito(reviewer=reviewer, stato="OK")
            e.t_rel = inizio
            return e

        s.esegui = finto
        try:
            budget = s.Budget(cap_token=10**9, secondi=30)
            t0 = time.perf_counter()
            esiti, interrotta = asyncio.run(
                s.esegui_tutti(s.REVIEWERS, "target", budget, 30)
            )
            durata = time.perf_counter() - t0
        finally:
            s.esegui = originali
        self.assertEqual(len(esiti), 4)
        self.assertFalse(interrotta)
        # In parallelo: ~0.3s, non ~1.2s.
        self.assertLess(durata, 0.8)

    def test_tetto_tempo_complessivo_interrompe(self):
        async def finto(reviewer, target, budget, tetto):
            await asyncio.sleep(5)  # piu' del tetto complessivo
            return s.Esito(reviewer=reviewer, stato="OK")

        s.esegui_originale = s.esegui
        s.esegui = finto
        try:
            budget = s.Budget(cap_token=10**9, secondi=0.3)
            _, interrotta = asyncio.run(s.esegui_tutti(s.REVIEWERS, "target", budget, 30))
        finally:
            s.esegui = s.esegui_originale
        self.assertTrue(interrotta)


if __name__ == "__main__":
    unittest.main(verbosity=2)
