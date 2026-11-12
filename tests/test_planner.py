"""验证可执行配餐、营养加总和无法满足约束时的报告。"""

import unittest
from dataclasses import replace

from diet_mvp.foods.catalog import load_catalog
from diet_mvp.nutrition.bmi_energy import calculate_reference_energy
from diet_mvp.nutrition.interfaces import ActivityLevel, PersonProfile, Sex
from diet_mvp.planner.recommender import recommend_day


class PlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.energy = calculate_reference_energy(PersonProfile(
            Sex.FEMALE, 28, 168, 65, ActivityLevel.LOW_ACTIVE))
        cls.plan = recommend_day(cls.energy, cls.catalog)

    def test_reference_plan_has_four_meals_and_energy_within_ten_percent(self):
        self.assertEqual(len(self.plan.meals), 4)
        self.assertTrue(all(1 <= len(meal.items) <= 3 for meal in self.plan.meals))
        self.assertLessEqual(abs(self.plan.totals.kcal / self.energy.daily_goal_kcal - 1), 0.10)
        self.assertTrue(self.plan.energy_within_tolerance)
        self.assertEqual([m.target_kcal / self.plan.target_kcal for m in self.plan.meals],
                         [0.3, 0.4, 0.2, 0.1])

    def test_reference_macro_percentages_are_in_trs916_ranges(self):
        for name, lower, upper in [("carbs_pct", 0.55, 0.75), ("fat_pct", 0.15, 0.30),
                                   ("protein_pct", 0.10, 0.15)]:
            self.assertGreaterEqual(self.plan.macro_percentages[name], lower)
            self.assertLessEqual(self.plan.macro_percentages[name], upper)
        self.assertTrue(self.plan.constraints_met)

    def test_portions_groups_and_diversity(self):
        staples, proteins = [], []
        for meal in self.plan.meals:
            groups = [item.food_group for item in meal.items]
            self.assertEqual(len(groups), len(set(groups)))
            self.assertTrue({"protein", "dairy"} & set(groups))
            self.assertTrue({"staple", "fruit"} & set(groups))
            if meal.name in ("lunch", "dinner"):
                self.assertIn("vegetable", groups)
            for item in meal.items:
                self.assertGreaterEqual(item.grams, 5 if item.food_group == "fat" else 50)
                self.assertLessEqual(item.grams, 20 if item.food_group == "fat" else 400)
                if item.food_group == "staple": staples.append(item.food_id)
                if item.food_group == "protein": proteins.append(item.food_id)
        self.assertEqual(len(staples), len(set(staples)))
        self.assertEqual(len(proteins), len(set(proteins)))

    def test_nutrient_totals_recompute_from_catalog(self):
        by_id = {food.id: food for food in self.catalog}
        for field in ("kcal", "carbs_g", "fat_g", "protein_g"):
            expected = sum(getattr(by_id[item.food_id].per_100g, field) * item.grams / 100
                           for meal in self.plan.meals for item in meal.items)
            self.assertAlmostEqual(getattr(self.plan.totals, field), expected)
            self.assertAlmostEqual(getattr(self.plan.totals, field),
                                   sum(getattr(meal.totals, field) for meal in self.plan.meals))
        self.assertAlmostEqual(self.plan.macro_percentages["protein_pct"],
                               self.plan.totals.protein_g * 4 / self.plan.totals.kcal)

    def test_limited_catalog_still_returns_closest_with_reasons(self):
        rice = [f for f in self.catalog if f.id == "rice_cooked"]
        plan = recommend_day(self.energy, rice)
        self.assertTrue(all(meal.items for meal in plan.meals))
        self.assertFalse(plan.constraints_met)
        self.assertTrue(plan.warnings)
        self.assertTrue(any("蛋白质" in text or "食物组" in text for text in plan.warnings))

    def test_extreme_goal_does_not_claim_feasibility(self):
        plan = recommend_day(replace(self.energy, daily_goal_kcal=20000), self.catalog[:1])
        self.assertFalse(plan.energy_within_tolerance)
        self.assertTrue(any("热量" in text for text in plan.warnings))

    def test_nonpositive_goal_and_empty_catalog_are_explicit(self):
        for goal in (0, -100):
            plan = recommend_day(replace(self.energy, daily_goal_kcal=goal), self.catalog)
            self.assertFalse(plan.constraints_met)
            self.assertTrue(plan.warnings)
            self.assertEqual(plan.totals.kcal, 0)
            self.assertTrue(all(not meal.items for meal in plan.meals))
        with self.assertRaises(ValueError):
            recommend_day(self.energy, [])

    def test_tiny_positive_goal_returns_closest_without_score_overflow(self):
        for goal in (1e-200, 1e-320):
            plan = recommend_day(replace(self.energy, daily_goal_kcal=goal), self.catalog[:1])
            self.assertTrue(all(meal.items for meal in plan.meals))
            self.assertFalse(plan.energy_within_tolerance)
            self.assertTrue(plan.warnings)
            # 极端目标的结果也应能按 CLI 的严格 JSON 规则编码。
            import json
            from dataclasses import asdict
            json.dumps(asdict(plan), allow_nan=False)


if __name__ == "__main__":
    unittest.main()
