import contextlib
import io
import unittest
from unittest.mock import Mock, patch

from tools import flight_tool


QUERY = "Create a 7 day plan for travel from kochi, kerala to copenhagen, denmark."


class FlightSearchTests(unittest.TestCase):
    def test_routes(self):
        cases = {
            QUERY: ("COK", "CPH"),
            "Flights from Kochi, Kerala, India to Copenhagen, Denmark": ("COK", "CPH"),
            "Flights to Copenhagen, Denmark from Kochi, Kerala": ("COK", "CPH"),
            "Plan a 7 days Japan trip from Bangladesh": ("DAC", "NRT"),
            "COK to CPH": ("COK", "CPH"),
            "all country flight info": (None, None),
            "all flights from Copenhagen": ("CPH", None),
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(flight_tool.parse_route(query), expected)

    def test_city_takes_precedence_over_country(self):
        for location, expected in [("Copenhagen, Denmark", "CPH"), ("Denmark", "CPH"),
                                   ("Mumbai, India", "BOM"), ("Cochin, Kerala", "COK"),
                                   ("Helsinki, Finland", "HEL")]:
            with self.subTest(location=location):
                self.assertEqual(flight_tool.resolve_location_to_iata(location), expected)

    def test_unknown_location_does_not_select_random_international_airport(self):
        self.assertIsNone(flight_tool.resolve_location_to_iata("Notarealplace"))
        self.assertIsNone(flight_tool.resolve_location_to_iata("Notarealplace, Denmark"))
        self.assertIsNone(flight_tool.country_name_to_code("Phuket"))

    @patch.object(flight_tool, "API_KEY", "test-secret")
    @patch.object(flight_tool.requests, "get")
    def test_search_sends_correct_filters_and_returns_results(self, get):
        get.return_value = Mock(json=Mock(return_value={"data": [{
            "airline": {"name": "Test Airline"}, "flight": {"iata": "TEST123"},
            "departure": {"iata": "COK"}, "arrival": {"iata": "CPH"},
        }]}))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = flight_tool.search_flights(QUERY)
        self.assertEqual(get.call_args.kwargs["params"], {
            "access_key": "test-secret", "limit": 10, "dep_iata": "COK", "arr_iata": "CPH",
        })
        self.assertIn("TEST123", result)
        self.assertNotIn("test-secret", output.getvalue())

    @patch.object(flight_tool, "API_KEY", "test-secret")
    @patch.object(flight_tool.requests, "get")
    def test_unresolved_route_never_fetches_global_flights(self, get):
        result = flight_tool.search_flights("Flights from Notarealplace to Copenhagen")
        self.assertIn("Flight route error", result)
        get.assert_not_called()

    @patch.object(flight_tool, "API_KEY", "test-secret")
    @patch.object(flight_tool.requests, "get")
    def test_empty_route_explains_connection_limitation(self, get):
        get.return_value = Mock(json=Mock(return_value={"data": []}))
        result = flight_tool.search_flights(QUERY)
        self.assertIn("COK to CPH", result)
        self.assertIn("not connecting itineraries", result)
        self.assertEqual(get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
