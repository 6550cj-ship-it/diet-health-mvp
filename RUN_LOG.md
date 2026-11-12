# 运行与验收记录

任务日期为 2026-11-10。执行目录为 `/Users/jcao/tmp/diet-health-mvp`。

## 环境

```text
Python 3.14.6
Python 3.11.15
```

未初始化 Git，未创建虚拟环境，未安装依赖。原有 `PROMPT.md`、`codex-last.txt` 保留。

## 完整测试

```bash
python3 -m unittest discover -s tests -v
```

```text
test_chinese_demo (test_cli.CLITests.test_chinese_demo) ... ok
test_help_and_bad_input (test_cli.CLITests.test_help_and_bad_input) ... ok
test_json_demo_is_machine_readable (test_cli.CLITests.test_json_demo_is_machine_readable) ... ok
test_bad_catalog_rejected (test_foods.FoodTests.test_bad_catalog_rejected) ... ok
test_local_catalog_has_balanced_groups_and_explicit_sources (test_foods.FoodTests.test_local_catalog_has_balanced_groups_and_explicit_sources) ... ok
test_off_impossible_per_100g_values_do_not_enter_catalog (test_foods.FoodTests.test_off_impossible_per_100g_values_do_not_enter_catalog) ... ok
test_off_multiple_food_groups_are_not_classified_as_single_ingredient (test_foods.FoodTests.test_off_multiple_food_groups_are_not_classified_as_single_ingredient) ... ok
test_off_network_or_malformed_response_silently_preserves_local (test_foods.FoodTests.test_off_network_or_malformed_response_silently_preserves_local) ... ok
test_off_parses_per_100g_and_skips_incomplete_products (test_foods.FoodTests.test_off_parses_per_100g_and_skips_incomplete_products) ... ok
test_age_notice (test_nutrition_contract.NutritionContractTests.test_age_notice) ... ok
test_all_bmi_boundaries_use_unrounded_value (test_nutrition_contract.NutritionContractTests.test_all_bmi_boundaries_use_unrounded_value) ... ok
test_all_pa_categories (test_nutrition_contract.NutritionContractTests.test_all_pa_categories) ... ok
test_bmi_example (test_nutrition_contract.NutritionContractTests.test_bmi_example) ... ok
test_female_reference_and_macro_grams (test_nutrition_contract.NutritionContractTests.test_female_reference_and_macro_grams) ... ok
test_invalid_input_raises_value_error (test_nutrition_contract.NutritionContractTests.test_invalid_input_raises_value_error) ... ok
test_low_calorie_exact_threshold_is_not_warning (test_nutrition_contract.NutritionContractTests.test_low_calorie_exact_threshold_is_not_warning) ... ok
test_low_calorie_thresholds_without_clamping (test_nutrition_contract.NutritionContractTests.test_low_calorie_thresholds_without_clamping) ... ok
test_male_sedentary_hand_calculation (test_nutrition_contract.NutritionContractTests.test_male_sedentary_hand_calculation) ... ok
test_non_binary_profiles (test_nutrition_contract.NutritionContractTests.test_non_binary_profiles) ... ok
test_weight_goal_adjustments_and_macros_use_daily_goal (test_nutrition_contract.NutritionContractTests.test_weight_goal_adjustments_and_macros_use_daily_goal) ... ok
test_extreme_goal_does_not_claim_feasibility (test_planner.PlannerTests.test_extreme_goal_does_not_claim_feasibility) ... ok
test_limited_catalog_still_returns_closest_with_reasons (test_planner.PlannerTests.test_limited_catalog_still_returns_closest_with_reasons) ... ok
test_nonpositive_goal_and_empty_catalog_are_explicit (test_planner.PlannerTests.test_nonpositive_goal_and_empty_catalog_are_explicit) ... ok
test_nutrient_totals_recompute_from_catalog (test_planner.PlannerTests.test_nutrient_totals_recompute_from_catalog) ... ok
test_portions_groups_and_diversity (test_planner.PlannerTests.test_portions_groups_and_diversity) ... ok
test_reference_macro_percentages_are_in_trs916_ranges (test_planner.PlannerTests.test_reference_macro_percentages_are_in_trs916_ranges) ... ok
test_reference_plan_has_four_meals_and_energy_within_ten_percent (test_planner.PlannerTests.test_reference_plan_has_four_meals_and_energy_within_ten_percent) ... ok
test_tiny_positive_goal_returns_closest_without_score_overflow (test_planner.PlannerTests.test_tiny_positive_goal_returns_closest_without_score_overflow) ... ok

----------------------------------------------------------------------
Ran 28 tests in 1.675s

OK
```

退出码为 0。

```bash
python3.11 -m unittest discover -s tests -v
```

```text

----------------------------------------------------------------------
Ran 28 tests in 1.701s

OK
```

退出码为 0。两种 Python 版本均为 28 项测试通过。覆盖契约数值、BMI 边界、PA、热量调整、阈值、非二元参考类型、非法输入、食物来源、OFF 解析及失败回退、复合分类、配餐加总与达标标识、极端目标以及 CLI。

## 中文 CLI 示例

```bash
python3 -m diet_mvp plan --sex female --age 28 --height-cm 168 --weight-kg 65 --activity low_active --goal maintain
```

```text
BMI 23.0，正常（normal，WHO 成人分级）
按未舍入 BMI 分级，显示一位小数。成人群体筛查指标，不能区分肌肉与脂肪；不用于未成年人分级诊断。
TDEE 2255.4 kcal/日，PA 1.14
日目标 2255.4 kcal，体重目标调整 +0 kcal
宏量目标：碳水 338.3 g（60%），脂肪 62.6 g（25%），蛋白质 84.6 g（15%）
WHO TRS 916 范围：碳水 55–75%，脂肪 15–30%，蛋白质 10–15%
群体水平估计，非个体能量消耗测量。未加运动热量或手动偏移，未做每周速率和目标体重渐减。

早餐，参考 676.6 kcal
  甜玉米粒（熟） 350 g，336.0 kcal，碳水 73.4 g，脂肪 5.2 g，蛋白质 11.9 g
  全脂牛奶 400 g，244.0 kcal，碳水 19.2 g，脂肪 13.0 g，蛋白质 12.6 g
  葡萄（可食部分） 150 g，103.5 kcal，碳水 27.2 g，脂肪 0.2 g，蛋白质 1.1 g
  小计 683.5 kcal

午餐，参考 902.2 kcal
  糙米饭（熟） 400 g，492.0 kcal，碳水 102.3 g，脂肪 3.9 g，蛋白质 11.0 g
  鸡蛋（煮熟，去壳） 150 g，232.5 kcal，碳水 1.7 g，脂肪 15.9 g，蛋白质 18.9 g
  胡萝卜（熟） 300 g，105.0 kcal，碳水 24.7 g，脂肪 0.5 g，蛋白质 2.3 g
  小计 829.5 kcal

晚餐，参考 451.1 kcal
  白米饭（熟） 150 g，195.0 kcal，碳水 42.3 g，脂肪 0.4 g，蛋白质 4.0 g
  全脂牛奶 400 g，244.0 kcal，碳水 19.2 g，脂肪 13.0 g，蛋白质 12.6 g
  胡萝卜（熟） 50 g，17.5 kcal，碳水 4.1 g，脂肪 0.1 g，蛋白质 0.4 g
  小计 456.5 kcal

加餐，参考 225.5 kcal
  梨（可食部分） 200 g，114.0 kcal，碳水 30.5 g，脂肪 0.3 g，蛋白质 0.7 g
  原味全脂酸奶 150 g，91.5 kcal，碳水 7.0 g，脂肪 4.9 g，蛋白质 5.2 g
  核桃仁 5 g，32.7 kcal，碳水 0.7 g，脂肪 3.3 g，蛋白质 0.8 g
  小计 238.2 kcal

整日合计 2207.7 kcal，目标 2255.4 kcal，差值 -47.7 kcal
碳水 352.1/338.3 g，脂肪 60.8/62.6 g，蛋白质 81.4/84.6 g（实际/目标）
实际供能比：碳水 63.8%，脂肪 24.8%，蛋白质 14.8%
热量 ±10% 达标：是；宏量范围达标：是

群体水平估计与离线配餐演示，非医疗建议。未评估过敏、疾病、孕哺期及微量营养素。
```

退出码为 0。计划相对目标的热量偏差为 -2.11%，四餐均有食物，热量与三个宏量范围同时达标。

## JSON 与标准库运行

```bash
python3 -m diet_mvp plan --sex female --age 28 --height-cm 168 --weight-kg 65 --activity low_active --goal maintain --json
```

退出码为 0，输出用 `json.loads` 解析并核查 BMI、四餐数量和达标字段。关键输出如下。

```json
{
  "bmi": 23,
  "category": "normal",
  "tdee_kcal": 2255.3826400000003,
  "daily_goal_kcal": 2255.3826400000003,
  "total_kcal": 2207.7,
  "macro_percentages": {
    "carbs_pct": 0.6380223762286542,
    "fat_pct": 0.24765796983285776,
    "protein_pct": 0.14753182044661867
  },
  "constraints_met": true,
  "catalog": {
    "local_count": 34,
    "off_added_count": 0
  }
}
```

```bash
python3.11 -B -S -m diet_mvp plan --sex female --age 28 --height-cm 168 --weight-kg 65 --activity low_active --goal maintain
```

退出码为 0，中文输出及营养结果与上例相同。`-S` 禁用 site 初始化，验证无需第三方包。

已额外以抛出异常的 `urlopen` 替身执行默认 CLI 并解析其 JSON，正常退出，证明默认流程没有发出网络请求。`--help`、`plan --help` 及错误输入的非零退出码均由 CLI 测试覆盖。

## 修复与复验

独立只读审查发现三个边界问题，均先加入失败回归测试，再修复并复验。

- OFF 的异常有限数值可能造成评分溢出。每 100 g 入口现拒绝超过 1000 kcal 或单项宏量超过 100 g 的条目，保留本地目录。
- 极小正热量目标可能使平方评分溢出。评分归一化设置下限，不能表示的比例偏差输出 null 并说明，仍给出未达标方案。
- 商品同时命中多个食物组时现归入 other，避免误当作单一类别。

独立复验确认 Python 3.11 和 3.14 各 28 项测试通过，无剩余 Critical 或 Important 问题。OFF 使用模拟成功响应及网络/格式失败响应验证，本环境未验证真实联网搜索的可用性。

配餐为启发式方案，不证明全局最优。食物为通用演示值，不声称逐条对应 FDC 原始记录。临床适用性和营养充分性不属于本次软件验收结论。


## 文件树

在仓库根用 Python 标准库 pathlib 递归枚举，按目录和名称排序，排除 __pycache__ 和 .git。实际输出如下。

```text
diet-health-mvp/
├── data/
│   └── sample_foods.json
├── diet_mvp/
│   └── __init__.py
├── docs/
│   └── superpowers/
│       └── plans/
│           └── 2026-11-10-diet-mvp.md
├── src/
│   └── diet_mvp/
│       ├── foods/
│       │   ├── __init__.py
│       │   ├── catalog.py
│       │   └── off_client.py
│       ├── nutrition/
│       │   ├── __init__.py
│       │   ├── bmi_energy.py
│       │   └── interfaces.py
│       ├── planner/
│       │   ├── __init__.py
│       │   └── recommender.py
│       ├── __init__.py
│       ├── __main__.py
│       └── cli.py
├── tests/
│   ├── test_cli.py
│   ├── test_foods.py
│   ├── test_nutrition_contract.py
│   └── test_planner.py
├── .gitignore
├── INTERFACE.md
├── PROMPT.md
├── README.md
├── RUN_LOG.md
└── codex-last.txt
```
