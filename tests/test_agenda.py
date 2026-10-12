"""Rules of the programme: past events, moments, headings, prices, search.

Run with: python -m unittest discover tests
"""
import unittest
from datetime import date, datetime

import agenda
from seed_data import build_demo_events

MONDAY = date(2026, 10, 12)


def evt(id_, day, end="", time="", category="Musique", price=""):
    return {"id": id_, "title": id_, "date": day, "end_date": end, "time": time,
            "category": category, "price": price}


def ids(programme, key):
    moment = next(m for m in programme["moments"] if m["key"] == key)
    return [i for block in moment["days"] for i in block["ids"]]


class ProgrammeTest(unittest.TestCase):
    def test_past_events_are_dropped_using_end_date(self):
        p = agenda.build_programme([
            evt("past", "2026-10-11"),
            evt("running", "2026-09-01", end="2026-10-20"),
            evt("ended", "2026-09-01", end="2026-10-11"),
        ], MONDAY)
        self.assertEqual([e["id"] for e in p["events"]], ["running"])

    def test_moments_and_sorting_by_time(self):
        p = agenda.build_programme([
            evt("late", "2026-10-12", time="23:00"),
            evt("early", "2026-10-12", time="19:00"),
            evt("no-time", "2026-10-12"),
            evt("tue", "2026-10-13"),
            evt("wed", "2026-10-14"),
            evt("sat", "2026-10-17"),
            evt("next-week", "2026-10-21"),
        ], MONDAY)
        self.assertEqual(ids(p, "tonight"), ["early", "late", "no-time"])
        self.assertEqual(ids(p, "tomorrow"), ["tue"])
        self.assertEqual(ids(p, "weekend"), ["sat"])
        self.assertEqual(ids(p, "later"), ["wed", "next-week"])
        counts = {m["key"]: m["count"] for m in p["moments"]}
        self.assertEqual(counts, {"tonight": 3, "tomorrow": 1, "weekend": 1, "later": 2})

    def test_undated_events_are_kept_last_in_later(self):
        p = agenda.build_programme([evt("x", "")], MONDAY)
        later = next(m for m in p["moments"] if m["key"] == "later")
        self.assertEqual(later["days"], [{"date": None, "ids": ["x"]}])

    def test_today_uses_swiss_time(self):
        # 23:30 UTC on Sunday is already Monday 01:30 in Lausanne.
        utc = datetime.fromisoformat("2026-10-11T23:30:00+00:00")
        self.assertEqual(agenda.today_local(utc), MONDAY)

    def test_weekend_on_sunday_is_today_only(self):
        self.assertEqual(agenda.weekend_days(date(2026, 10, 18)),
                         (date(2026, 10, 18), date(2026, 10, 18)))


class RubricPriceSearchTest(unittest.TestCase):
    def test_rubrics(self):
        self.assertEqual(agenda.rubric_for("Clubbing"), "Soirées & clubs")
        self.assertEqual(agenda.rubric_for("Humour"), "Scène")
        self.assertEqual(agenda.rubric_for("Festival"), "Autres")
        self.assertEqual(agenda.rubric_for(""), "Autres")

    def test_prices_are_never_guessed(self):
        self.assertFalse(agenda.read_price("")["known"])
        self.assertFalse(agenda.read_price("Voir détails")["known"])
        self.assertTrue(agenda.read_price("Entrée libre")["is_free"])
        self.assertEqual(agenda.read_price("CHF 35–85")["price_min"], 35)
        self.assertEqual(agenda.read_price("CHF 45 / jour — CHF 110 / 3 jours")["price_min"], 45)
        self.assertIsNone(agenda.read_price("dès 16 ans")["price_min"])

    def test_small_price_rule(self):
        self.assertTrue(agenda.is_small_price(agenda.read_price("CHF 15")))
        self.assertFalse(agenda.is_small_price(agenda.read_price("CHF 18")))
        self.assertFalse(agenda.is_small_price(agenda.read_price("")))

    def test_search_ignores_accents(self):
        self.assertTrue(agenda.matches({"title": "La Traviata", "location": "Opéra de Lausanne"}, "opera"))
        self.assertTrue(agenda.matches({"title": "Théâtre"}, "THEATRE"))
        self.assertFalse(agenda.matches({"title": "Jazz"}, "opera"))


class DemoDataTest(unittest.TestCase):
    def test_demo_is_never_all_past(self):
        p = agenda.build_programme(build_demo_events(MONDAY), MONDAY)
        self.assertGreater(ids(p, "tonight").__len__(), 3)
        self.assertGreater(ids(p, "weekend").__len__(), 3)


if __name__ == "__main__":
    unittest.main()
