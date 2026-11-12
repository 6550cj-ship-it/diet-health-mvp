"""中文命令行和可序列化 JSON 输出。"""

import argparse
import json
from dataclasses import asdict

from .foods.catalog import load_catalog
from .foods.off_client import supplement_catalog
from .nutrition.bmi_energy import calculate_bmi, calculate_reference_energy
from .nutrition.interfaces import ActivityLevel, CaloriesProfile, PersonProfile, Sex, WeightGoal
from .planner.recommender import recommend_day


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="饮食健康离线 MVP，群体参考估计，非医疗建议。")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="计算 BMI、参考热量并推荐一日四餐")
    plan.add_argument("--sex", choices=[item.value for item in Sex], required=True, help="公式参考类别")
    plan.add_argument("--age", type=int, required=True, help="整数年龄，至少 13 岁")
    plan.add_argument("--height-cm", type=float, required=True, help="身高，厘米")
    plan.add_argument("--weight-kg", type=float, required=True, help="体重，公斤")
    plan.add_argument("--activity", choices=[item.value for item in ActivityLevel], required=True, help="活动等级")
    plan.add_argument("--goal", choices=[item.value for item in WeightGoal], default="maintain", help="体重目标")
    plan.add_argument("--calories-profile", choices=[item.value for item in CaloriesProfile],
                      default="averaged", help="non_binary 的参考公式选择，其他性别忽略此选项")
    plan.add_argument("--use-off", metavar="关键词", help="可选联网搜索 Open Food Facts，失败时保留本地库")
    plan.add_argument("--json", action="store_true", help="输出结构化 JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        profile = PersonProfile(Sex(args.sex), args.age, args.height_cm, args.weight_kg,
                                ActivityLevel(args.activity), CaloriesProfile(args.calories_profile),
                                WeightGoal(args.goal))
        bmi = calculate_bmi(profile.weight_kg, profile.height_cm)
        energy = calculate_reference_energy(profile)
        foods = load_catalog()
        local_count = len(foods)
        if args.use_off:
            foods = supplement_catalog(foods, args.use_off)
        plan = recommend_day(energy, foods)
    except ValueError as exc:
        parser.error(str(exc))
    disclaimer = "群体水平估计与离线配餐演示，非医疗建议。未评估过敏、疾病、孕哺期及微量营养素。"
    if args.json:
        payload = {"profile": asdict(profile), "bmi": asdict(bmi), "energy": asdict(energy),
                   "plan": asdict(plan), "catalog": {"local_count": local_count,
                   "off_added_count": len(foods) - local_count}, "disclaimer": disclaimer}
        print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    print(f"BMI {bmi.bmi:.1f}，{bmi.category_label_zh}（{bmi.category.value}，WHO 成人分级）")
    print(bmi.notes)
    print(f"TDEE {energy.tdee_kcal:.1f} kcal/日，PA {energy.pa_coefficient:g}")
    print(f"日目标 {energy.daily_goal_kcal:.1f} kcal，体重目标调整 {energy.weight_goal_adjustment_kcal:+.0f} kcal")
    macro = energy.macros
    print(f"宏量目标：碳水 {macro.carbs_g:.1f} g（60%），脂肪 {macro.fat_g:.1f} g（25%），蛋白质 {macro.protein_g:.1f} g（15%）")
    print("WHO TRS 916 范围：碳水 55–75%，脂肪 15–30%，蛋白质 10–15%")
    if energy.age_notice:
        print("年龄提示：" + energy.age_notice)
    if energy.low_calorie_warning:
        print("低热量提示：日目标低于所选参考类型的提示阈值，未钳制目标，请咨询专业人员。")
    print(energy.notes)
    for meal in plan.meals:
        print(f"\n{meal.name_zh}，参考 {meal.target_kcal:.1f} kcal")
        for item in meal.items:
            n = item.nutrients
            print(f"  {item.name_zh} {item.grams:g} g，{n.kcal:.1f} kcal，碳水 {n.carbs_g:.1f} g，脂肪 {n.fat_g:.1f} g，蛋白质 {n.protein_g:.1f} g")
        print(f"  小计 {meal.totals.kcal:.1f} kcal")
    n = plan.totals
    print(f"\n整日合计 {n.kcal:.1f} kcal，目标 {plan.target_kcal:.1f} kcal，差值 {plan.calorie_difference_kcal:+.1f} kcal")
    print(f"碳水 {n.carbs_g:.1f}/{macro.carbs_g:.1f} g，脂肪 {n.fat_g:.1f}/{macro.fat_g:.1f} g，蛋白质 {n.protein_g:.1f}/{macro.protein_g:.1f} g（实际/目标）")
    p = plan.macro_percentages
    print(f"实际供能比：碳水 {p['carbs_pct']:.1%}，脂肪 {p['fat_pct']:.1%}，蛋白质 {p['protein_pct']:.1%}")
    print(f"热量 ±10% 达标：{'是' if plan.energy_within_tolerance else '否'}；宏量范围达标：{'是' if plan.macro_ranges_met else '否'}")
    for warning in plan.warnings:
        print("配餐提示：" + warning)
    print("\n" + disclaimer)
    return 0
