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

    def test_weekly_schedule_shows_only_on_its_weekday(self):
        # Every Thursday at 18:00 from July to December (read on the event's page).
        thursdays = evt("afterwork", "2026-07-23", end="2026-12-24")
        thursdays["schedule"] = [{"from": "2026-07-23", "to": "2026-12-24", "times": {"3": ["18:00"]}}]
        p = agenda.build_programme([thursdays], MONDAY)
        self.assertEqual([ids(p, k) for k in ("tonight", "tomorrow", "weekend")], [[], [], []])
        later = next(m for m in p["moments"] if m["key"] == "later")
        self.assertEqual(later["days"], [{"date": "2026-10-15", "ids": ["afterwork"], "times": {"afterwork": "18:00"}}])
        [event] = p["events"]
        self.assertEqual((event["next_date"], event["time"]), ("2026-10-15", "18:00"))
        self.assertNotIn("schedule", event)

    def test_dates_of_a_schedule_keep_their_own_times(self):
        show = evt("lambiel", "2026-10-13", end="2026-10-18")
        show["schedule"] = [{"from": "2026-10-13", "to": "2026-10-13", "times": {"1": ["20:00"]}},
                            {"from": "2026-10-18", "to": "2026-10-18", "times": {"6": ["14:00"]}}]
        p = agenda.build_programme([show], MONDAY)
        days = {m["key"]: m["days"] for m in p["moments"]}
        self.assertEqual(days["tonight"], [])
        self.assertEqual(days["tomorrow"][0]["times"], {"lambiel": "20:00"})
        self.assertEqual(days["weekend"], [{"date": "2026-10-18", "ids": ["lambiel"], "times": {"lambiel": "14:00"}}])

    def test_schedule_without_times_keeps_the_day_and_an_unknown_time(self):
        film = evt("film", "2026-10-12")
        film["schedule"] = [{"from": "2026-10-12", "to": "2026-10-12", "times": {}}]
        p = agenda.build_programme([film], MONDAY)
        self.assertEqual(next(m for m in p["moments"] if m["key"] == "tonight")["days"][0]["times"], {"film": ""})

    def test_schedule_over_before_the_listed_end_is_past(self):
        series = evt("series", "2026-09-01", end="2026-12-31")
        series["schedule"] = [{"from": "2026-09-01", "to": "2026-09-01", "times": {"1": ["19:00"]}}]
        self.assertEqual(agenda.build_programme([series], MONDAY)["events"], [])

    def test_undated_events_are_kept_last_in_later(self):
        p = agenda.build_programme([evt("x", "")], MONDAY)
        later = next(m for m in p["moments"] if m["key"] == "later")
        self.assertEqual(later["days"], [{"date": None, "ids": ["x"], "times": {"x": ""}}])

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
