"""生成餐次候选，再用有界束搜索平衡整日营养和食物多样性。"""

import math
from dataclasses import dataclass
from itertools import product

from ..foods.catalog import Food, Nutrients, sum_nutrients
from ..nutrition.interfaces import EnergyResult, MacroTarget

MEALS = (("breakfast", "早餐", 0.30), ("lunch", "午餐", 0.40),
         ("dinner", "晚餐", 0.20), ("snack", "加餐", 0.10))


@dataclass(frozen=True)
class Serving:
    food_id: str
    name_zh: str
    food_group: str
    grams: float
    nutrients: Nutrients
    source: str


@dataclass(frozen=True)
class MealPlan:
    name: str
    name_zh: str
    target_kcal: float
    items: tuple[Serving, ...]
    totals: Nutrients


@dataclass(frozen=True)
class DailyPlan:
    meals: tuple[MealPlan, ...]
    totals: Nutrients
    target_kcal: float
    target_macros: MacroTarget
    macro_percentages: dict[str, float]
    macro_ranges: dict[str, tuple[float, float]]
    calorie_difference_kcal: float
    calorie_difference_pct: float | None
    energy_within_tolerance: bool
    macro_ranges_met: bool
    constraints_met: bool
    warnings: tuple[str, ...]
    algorithm: str


@dataclass(frozen=True)
class _Candidate:
    foods: tuple[Food, ...]
    grams: tuple[int, ...]
    # 搜索阶段用元组降低枚举开销，顺序为热量、蛋白质、脂肪、碳水。
    values: tuple[float, float, float, float]
    score: float


def _portions(food: Food) -> tuple[int, ...]:
    if food.food_group == "fat":
        return (5, 10, 15, 20)
    if food.food_group == "protein":
        return tuple(range(50, 251, 50))
    if food.food_group in ("fruit", "vegetable"):
        return tuple(range(50, 301, 50))
    # 高密度主食限制干重，避免把大量干燕麦当作一份即食食品。
    if food.food_group == "staple" and food.per_100g.kcal >= 300:
        return (50, 100, 150)
    if food.food_group == "staple" and food.per_100g.kcal >= 220:
        return (50, 100, 150, 200)
    return tuple(range(50, 401, 50))


def _macro_pct(values: tuple[float, ...]) -> dict[str, float]:
    kcal, protein, fat, carbs = values
    if kcal <= 0:
        return {"carbs_pct": 0.0, "fat_pct": 0.0, "protein_pct": 0.0}
    # 分母使用食物库热量，保留纤维、食物专用系数和舍入造成的不一致。
    return {"carbs_pct": carbs * 4 / kcal, "fat_pct": fat * 9 / kcal,
            "protein_pct": protein * 4 / kcal}


def _ranges(energy: EnergyResult) -> dict[str, tuple[float, float]]:
    return {"carbs_pct": energy.carb_pct_range, "fat_pct": energy.fat_pct_range,
            "protein_pct": energy.protein_pct_range}


def _score(values: tuple[float, ...], target: float, energy: EnergyResult) -> float:
    kcal, protein, fat, carbs = values
    # 小于 1 kcal 的目标仍返回最近候选，评分归一化下限防止平方溢出。
    score = 12 * ((kcal - target) / max(target, 1.0)) ** 2
    for grams, share, density in [(protein, energy.macros.protein_pct, 4),
                                   (fat, energy.macros.fat_pct, 9),
                                   (carbs, energy.macros.carbs_pct, 4)]:
        expected = target * share / density
        score += ((grams - expected) / max(expected, 1)) ** 2
    pct = _macro_pct(values)
    for key, (lower, upper) in _ranges(energy).items():
        outside = max(lower - pct[key], 0, pct[key] - upper)
        score += 6 * (outside / (upper - lower)) ** 2
    return score


def _templates(name: str, groups: dict[str, list[Food]]) -> list[tuple[str, ...]]:
    if name == "breakfast":
        preferred = [("staple", "dairy", "fruit"), ("staple", "protein", "fruit")]
    elif name in ("lunch", "dinner"):
        preferred = [("staple", "protein", "vegetable"), ("staple", "dairy", "vegetable")]
    else:
        preferred = [("fruit", "dairy", "fat"), ("fruit", "dairy"), ("staple", "dairy")]
    available = [template for template in preferred if all(groups.get(group) for group in template)]
    if available:
        return available
    # 缺少必要食物组时，保留尽可能多的不同组，并在最终结果中明确缺项。
    order = ("staple", "protein", "vegetable", "dairy", "fruit", "other", "fat")
    return [tuple(group for group in order if groups.get(group))[:3]]


def _candidates(name: str, target: float, energy: EnergyResult,
                groups: dict[str, list[Food]]) -> list[_Candidate]:
    candidates = []
    for template in _templates(name, groups):
        for foods in product(*(groups[group] for group in template)):
            portions = [_portions(food) for food in foods]
            densities = [(food.per_100g.kcal / 100, food.per_100g.protein_g / 100,
                          food.per_100g.fat_g / 100, food.per_100g.carbs_g / 100) for food in foods]
            best = []
            # 枚举前两种食物的份量，最后一种选剩余热量附近的三个步进值。
            for prefix in product(*portions[:-1]):
                partial = tuple(sum(densities[i][j] * grams for i, grams in enumerate(prefix)) for j in range(4))
                remaining = (target - partial[0]) / densities[-1][0]
                options = sorted(portions[-1], key=lambda grams: abs(grams - remaining))[:3]
                for grams in options:
                    values = tuple(partial[j] + densities[-1][j] * grams for j in range(4))
                    score = _score(values, target, energy)
                    best.append((score, prefix + (grams,), values))
            # 每个食物组合保留两个份量方案，之后再统一截断，控制搜索规模。
            for score, grams, values in sorted(best, key=lambda item: item[0])[:2]:
                candidates.append(_Candidate(foods, grams, values, score))
    candidates.sort(key=lambda item: item.score)
    # 每个主食/蛋白质身份至少保留一个候选，再加入全局靠前候选。
    selected, seen = [], set()
    for candidate in candidates:
        identities = {food.id for food in candidate.foods if food.food_group in ("staple", "protein")}
        if identities - seen:
            selected.append(candidate)
            seen.update(identities)
    selected.extend(candidates[:96])
    return list(dict.fromkeys(selected))


def _structural_warnings(meals: tuple[MealPlan, ...]) -> list[str]:
    warnings = []
    for meal in meals:
        groups = {item.food_group for item in meal.items}
        if not groups.intersection({"protein", "dairy"}):
            warnings.append(f"{meal.name_zh}缺少蛋白质或乳制品食物组。")
        if not groups.intersection({"staple", "fruit"}):
            warnings.append(f"{meal.name_zh}缺少主食或水果食物组。")
        if meal.name in ("lunch", "dinner") and "vegetable" not in groups:
            warnings.append(f"{meal.name_zh}缺少蔬菜食物组。")
    for group, label in [("staple", "主食"), ("protein", "蛋白质食物")]:
        ids = [item.food_id for meal in meals for item in meal.items if item.food_group == group]
        if len(ids) != len(set(ids)):
            warnings.append(f"{label}有重复，当前候选未同时满足多样性偏好。")
    return warnings


def recommend_day(energy: EnergyResult, catalog: list[Food]) -> DailyPlan:
    """返回一个确定性主方案。无法达标时返回搜索中最接近的方案并说明。"""
    if not catalog:
        raise ValueError("食物目录不能为空")
    if not math.isfinite(energy.daily_goal_kcal):
        raise ValueError("日目标热量必须是有限数")
    groups: dict[str, list[Food]] = {}
    for food in sorted(catalog, key=lambda food: food.id):
        groups.setdefault(food.food_group, []).append(food)
    target = energy.daily_goal_kcal
    algorithm = "离散餐次候选 + 宽度 64 束搜索；启发式结果，不保证全局最优。"
    warnings = []
    if target <= 0:
        meals = tuple(MealPlan(name, zh, target * share, (), Nutrients()) for name, zh, share in MEALS)
        warnings.append("非正日目标不能用于配餐，未生成食物份量。请检查输入或参考公式适用性。")
    else:
        # 状态为候选序列、累计营养、已用主食/蛋白质、重复数、餐次偏差。
        beam = [((), (0.0, 0.0, 0.0, 0.0), frozenset(), 0, 0.0)]
        processed_share = 0.0
        for name, zh, share in MEALS:
            pool = _candidates(name, target * share, energy, groups)
            processed_share += share
            states = []
            for chosen, total, used, repeats, meal_error in beam:
                for candidate in pool:
                    values = tuple(total[j] + candidate.values[j] for j in range(4))
                    ids = frozenset(food.id for food in candidate.foods if food.food_group in ("staple", "protein"))
                    duplicate_count = repeats + len(ids & used)
                    allocation_error = meal_error + ((candidate.values[0] - target * share) / max(target, 1.0)) ** 2
                    score = _score(values, target * processed_share, energy) + 0.3 * duplicate_count + 3 * allocation_error
                    state = (chosen + (candidate,), values, used | ids, duplicate_count, allocation_error)
                    states.append((score, state))
            states.sort(key=lambda pair: pair[0])
            beam = [state for _, state in states[:64]]
        def final_rank(state):
            chosen, values, used, repeats, meal_error = state
            pct = _macro_pct(values)
            feasible = abs(values[0] / target - 1) <= 0.10 and all(
                lower <= pct[key] <= upper for key, (lower, upper) in _ranges(energy).items())
            return (not feasible, _score(values, target, energy) + repeats * 0.3 + meal_error * 3)
        chosen = min(beam, key=final_rank)[0]
        meal_list = []
        for (name, zh, share), candidate in zip(MEALS, chosen):
            items = tuple(Serving(food.id, food.name_zh, food.food_group, grams,
                                  food.per_100g.scaled(grams / 100), food.source)
                          for food, grams in zip(candidate.foods, candidate.grams))
            meal_list.append(MealPlan(name, zh, target * share, items,
                                      sum_nutrients(item.nutrients for item in items)))
        meals = tuple(meal_list)
    totals = sum_nutrients(meal.totals for meal in meals)
    pct = _macro_pct((totals.kcal, totals.protein_g, totals.fat_g, totals.carbs_g))
    energy_met = target > 0 and abs(totals.kcal / target - 1) <= 0.10
    ranges_met = totals.kcal > 0 and all(lower <= pct[key] <= upper
                                        for key, (lower, upper) in _ranges(energy).items())
    if not energy_met and target > 0:
        warnings.append("整日热量未达到目标的 ±10%，受当前食物目录、份量上限和有界搜索限制。")
    labels = {"protein_pct": "蛋白质", "fat_pct": "脂肪", "carbs_pct": "碳水化合物"}
    for key, (lower, upper) in _ranges(energy).items():
        if not lower <= pct[key] <= upper:
            warnings.append(f"{labels[key]}供能比 {pct[key]:.1%} 未在 {lower:.0%}–{upper:.0%} 内，当前候选和份量限制下未找到同时达标的方案。")
    if target > 0:
        warnings.extend(_structural_warnings(meals))
    difference_pct = totals.kcal / target - 1 if target > 0 else None
    if difference_pct is not None and not math.isfinite(difference_pct):
        difference_pct = None
        warnings.append("目标热量过小，比例偏差超出有限数值范围，仅报告 kcal 差值。")
    return DailyPlan(meals, totals, target, energy.macros, pct, _ranges(energy),
                     totals.kcal - target, difference_pct,
                     energy_met, ranges_met, energy_met and ranges_met, tuple(warnings), algorithm)
