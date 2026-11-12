"""离线目录和远程补充的边界行为。"""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from diet_mvp.foods.catalog import load_catalog
from diet_mvp.foods.off_client import search_foods, supplement_catalog


class FoodTests(unittest.TestCase):
    def test_local_catalog_has_balanced_groups_and_explicit_sources(self):
        foods = load_catalog()
        self.assertTrue(28 <= len(foods) <= 36)
        self.assertEqual(len({f.id for f in foods}), len(foods))
        self.assertTrue({"staple", "protein", "vegetable", "fruit", "dairy", "fat"}
                        <= {f.food_group for f in foods})
        for food in foods:
            self.assertIn("USDA-style generic public values for offline demo", food.source)
            self.assertTrue(food.name_zh and food.name_en)
            for value in (food.per_100g.kcal, food.per_100g.protein_g,
                          food.per_100g.fat_g, food.per_100g.carbs_g):
                self.assertGreaterEqual(value, 0)

    def test_bad_catalog_rejected(self):
        for payload in [[], {}, [{"id": "missing"}]]:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "foods.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_catalog(path)

    def test_off_parses_per_100g_and_skips_incomplete_products(self):
        payload = {"products": [
            {"code": "123", "product_name": "Plain yogurt", "product_name_zh": "原味酸奶",
             "categories_tags": ["en:yogurts"],
             "nutriments": {"energy-kcal_100g": 61, "proteins_100g": 3.5,
                            "fat_100g": 3.3, "carbohydrates_100g": 4.7}},
            {"code": "bad", "product_name": "Missing", "nutriments": {}},
            {"code": "nan", "product_name": "Non-finite", "nutriments": {
                "energy-kcal_100g": "NaN", "proteins_100g": 1, "fat_100g": 1, "carbohydrates_100g": 1}},
        ]}
        with patch("diet_mvp.foods.off_client.urlopen",
                   return_value=io.BytesIO(json.dumps(payload).encode())):
            foods = search_foods("yogurt")
        self.assertEqual(len(foods), 1)
        self.assertEqual(foods[0].id, "off_123")
        self.assertEqual(foods[0].food_group, "dairy")
        self.assertEqual(foods[0].per_100g.kcal, 61)
        self.assertEqual(foods[0].per_100g.protein_g, 3.5)
        self.assertIn("Open Food Facts", foods[0].source)

    def test_off_network_or_malformed_response_silently_preserves_local(self):
        local = load_catalog()
        cases = [URLError("offline"), b"not-json", b'{"products":null}',
                 b'{"products":[null,{},1]}', b'[]']
        for case in cases:
            kwargs = {"side_effect": case} if isinstance(case, Exception) else {"return_value": io.BytesIO(case)}
            output = io.StringIO()
            with self.subTest(case=case), patch("diet_mvp.foods.off_client.urlopen", **kwargs), \
                    redirect_stderr(output), redirect_stdout(output):
                result = supplement_catalog(local, "yogurt")
            self.assertEqual(result, local)
            self.assertEqual(output.getvalue(), "")

    def test_off_impossible_per_100g_values_do_not_enter_catalog(self):
        local = load_catalog()
        valid = {"energy-kcal_100g": 130, "proteins_100g": 3,
                 "fat_100g": 1, "carbohydrates_100g": 28}
        for key in valid:
            with self.subTest(key=key):
                values = dict(valid, **{key: 1e308})
                payload = {"products": [{"code": "invalid", "product_name": "Rice",
                           "categories_tags": ["en:rices"], "nutriments": values}]}
                with patch("diet_mvp.foods.off_client.urlopen",
                           return_value=io.BytesIO(json.dumps(payload).encode())):
                    result = supplement_catalog(local, "rice")
                self.assertEqual(result, local)

    def test_off_multiple_food_groups_are_not_classified_as_single_ingredient(self):
        payload = {"products": [{"code": "mixed", "product_name": "Rice with fish",
                   "categories_tags": ["en:rices", "en:fishes"],
                   "nutriments": {"energy-kcal_100g": 150, "proteins_100g": 10,
                                  "fat_100g": 3, "carbohydrates_100g": 20}}]}
        with patch("diet_mvp.foods.off_client.urlopen",
                   return_value=io.BytesIO(json.dumps(payload).encode())):
            foods = search_foods("rice")
        self.assertEqual(len(foods), 1)
        self.assertEqual(foods[0].food_group, "other")


if __name__ == "__main__":
    unittest.main()
