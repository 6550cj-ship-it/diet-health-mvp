"""营养计算的稳定契约，期望数值独立手算。"""

import unittest
from dataclasses import replace

from diet_mvp.nutrition.bmi_energy import calculate_bmi, calculate_reference_energy
from diet_mvp.nutrition.interfaces import (
    ActivityLevel, BMICategory, CaloriesProfile, PersonProfile, Sex, WeightGoal,
)


def example_profile(**changes):
    """构造任务给定的女性对照人物。"""
    return replace(PersonProfile(Sex.FEMALE, 28, 168, 65, ActivityLevel.LOW_ACTIVE), **changes)


class NutritionContractTests(unittest.TestCase):
    def test_bmi_example(self):
        result = calculate_bmi(65, 168)
        self.assertEqual(result.bmi, 23.0)
        self.assertEqual(result.category, BMICategory.NORMAL)
        self.assertEqual(result.category_label_zh, "正常")
        self.assertEqual(result.standard, "WHO adult BMI")

    def test_all_bmi_boundaries_use_unrounded_value(self):
        cases = [(18.49, "underweight"), (18.5, "normal"), (24.99, "normal"),
                 (25, "pre_obesity"), (29.99, "pre_obesity"), (30, "obesity_class_i"),
                 (34.99, "obesity_class_i"), (35, "obesity_class_ii"),
                 (39.99, "obesity_class_ii"), (40, "obesity_class_iii")]
        for bmi, category in cases:
            with self.subTest(bmi=bmi):
                self.assertEqual(calculate_bmi(bmi, 100).category.value, category)

    def test_female_reference_and_macro_grams(self):
        result = calculate_reference_energy(example_profile())
        # 10.9*65 + 660.7*1.68 = 1818.476，乘1.14再加182.32。
        self.assertAlmostEqual(result.tdee_kcal, 2255.38264, places=5)
        self.assertLessEqual(abs(result.tdee_kcal - 2255), 1)
        self.assertEqual(result.daily_goal_kcal, result.tdee_kcal)
        self.assertAlmostEqual(result.macros.carbs_g, 338.307396, places=5)
        self.assertAlmostEqual(result.macros.fat_g, 62.64951778, places=5)
        self.assertAlmostEqual(result.macros.protein_g, 84.576849, places=5)
        self.assertEqual(result.carb_pct_range, (0.55, 0.75))
        self.assertEqual(result.fat_pct_range, (0.15, 0.30))
        self.assertEqual(result.protein_pct_range, (0.10, 0.15))

    def test_male_sedentary_hand_calculation(self):
        # 864-291.6 + (1136+880.25) = 2588.65 kcal。
        result = calculate_reference_energy(example_profile(
            sex=Sex.MALE, age_years=30, weight_kg=80, height_cm=175,
            activity=ActivityLevel.SEDENTARY))
        self.assertAlmostEqual(result.tdee_kcal, 2588.65, delta=1)
        self.assertEqual(result.pa_coefficient, 1)

    def test_all_pa_categories(self):
        # 同一人物，四种活动等级的独立计算值。
        for activity, male, female in [
            (ActivityLevel.SEDENTARY, 2359.88, 2000.796),
            (ActivityLevel.LOW_ACTIVE, 2572.0448, 2255.38264),
            (ActivityLevel.ACTIVE, 2837.2508, 2491.78452),
            (ActivityLevel.VERY_ACTIVE, 3314.6216, 2819.1102),
        ]:
            for sex, expected in [(Sex.MALE, male), (Sex.FEMALE, female)]:
                with self.subTest(activity=activity, sex=sex):
                    result = calculate_reference_energy(example_profile(sex=sex, activity=activity))
                    self.assertAlmostEqual(result.tdee_kcal, expected, places=4)

    def test_weight_goal_adjustments_and_macros_use_daily_goal(self):
        for goal, delta in [(WeightGoal.LOSE, -500), (WeightGoal.MAINTAIN, 0),
                            (WeightGoal.GAIN, 500)]:
            result = calculate_reference_energy(example_profile(weight_goal=goal))
            self.assertEqual(result.weight_goal_adjustment_kcal, delta)
            self.assertAlmostEqual(result.daily_goal_kcal, 2255.38264 + delta)
            self.assertAlmostEqual(result.macros.carbs_g, (2255.38264 + delta) * 0.6 / 4)

    def test_non_binary_profiles(self):
        for activity in ActivityLevel:
            base = example_profile(activity=activity)
            male = calculate_reference_energy(replace(base, sex=Sex.MALE))
            female = calculate_reference_energy(base)
            averaged = calculate_reference_energy(replace(base, sex=Sex.NON_BINARY))
            self.assertAlmostEqual(averaged.tdee_kcal, (male.tdee_kcal + female.tdee_kcal) / 2)
            self.assertAlmostEqual(averaged.pa_coefficient,
                                   (male.pa_coefficient + female.pa_coefficient) / 2)
            for cp, expected in [(CaloriesProfile.ESTROGEN_TYPICAL, female),
                                 (CaloriesProfile.TESTOSTERONE_TYPICAL, male)]:
                result = calculate_reference_energy(replace(base, sex=Sex.NON_BINARY, calories_profile=cp))
                self.assertEqual(result.tdee_kcal, expected.tdee_kcal)

    def test_low_calorie_thresholds_without_clamping(self):
        # 年龄30、体重34时，男非身高项1055.2、女非身高项538.3。
        # 独立解方程得到阈值身高，再用微小改变量跨过阈值。
        for sex, cp, threshold, age, weight, height in [
            (Sex.MALE, CaloriesProfile.AVERAGED, 1500, 30, 34, 88.42942345924453),
            (Sex.FEMALE, CaloriesProfile.AVERAGED, 1200, 30, 34, 100.15135462388376),
            (Sex.NON_BINARY, CaloriesProfile.TESTOSTERONE_TYPICAL, 1500, 30, 34, 88.42942345924453),
            (Sex.NON_BINARY, CaloriesProfile.ESTROGEN_TYPICAL, 1200, 30, 34, 100.15135462388376),
            (Sex.NON_BINARY, CaloriesProfile.AVERAGED, 1200, 30, 34, 69.30480364355074),
        ]:
            base = example_profile(sex=sex, calories_profile=cp, age_years=age,
                                   weight_kg=weight, height_cm=height,
                                   activity=ActivityLevel.SEDENTARY)
            for offset, warning in [(-0.001, True), (0.001, False)]:
                with self.subTest(sex=sex, cp=cp, offset=offset):
                    result = calculate_reference_energy(replace(base, height_cm=height + offset))
                    self.assertAlmostEqual(result.daily_goal_kcal, threshold, delta=0.02)
                    self.assertEqual(result.low_calorie_warning, warning)

    def test_low_calorie_exact_threshold_is_not_warning(self):
        # 男 1500 = 864-369.36+291.1+714.26。
        # 女 1200 = 387-519.01+307.925+1024.085。
        for sex, age, weight, height, expected in [
            (Sex.MALE, 38, 20.5, 142, 1500),
            (Sex.FEMALE, 71, 28.25, 155, 1200),
        ]:
            result = calculate_reference_energy(example_profile(
                sex=sex, age_years=age, weight_kg=weight, height_cm=height,
                activity=ActivityLevel.SEDENTARY))
            self.assertEqual(result.daily_goal_kcal, expected)
            self.assertFalse(result.low_calorie_warning)

    def test_age_notice(self):
        for age in (13, 18, 19, 28):
            result = calculate_reference_energy(example_profile(age_years=age))
            if age < 19:
                self.assertIn("当前使用 19 岁及以上成人参考公式", result.age_notice)
            else:
                self.assertIsNone(result.age_notice)

    def test_invalid_input_raises_value_error(self):
        for invalid in (0, -1, float("nan"), float("inf"), "65", True, None):
            for field in ("weight_kg", "height_cm"):
                with self.subTest(field=field, value=invalid):
                    with self.assertRaises(ValueError):
                        calculate_reference_energy(example_profile(**{field: invalid}))
            with self.assertRaises(ValueError):
                calculate_bmi(invalid, 168)
            with self.assertRaises(ValueError):
                calculate_bmi(65, invalid)
        for age in (12, -1, 28.0, 13.5, True, "28", None):
            with self.subTest(age=age), self.assertRaises(ValueError):
                calculate_reference_energy(example_profile(age_years=age))
        for field in ("sex", "activity", "calories_profile", "weight_goal"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                calculate_reference_energy(example_profile(**{field: "unknown"}))


if __name__ == "__main__":
    unittest.main()
