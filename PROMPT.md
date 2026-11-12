# 任务：自建饮食健康 MVP 骨架 + 配餐核心

在本目录 `/Users/jcao/tmp/diet-health-mvp` 创建一个可本地运行的 Python 3.11+ 项目（不要整仓分叉任何现成大应用）。用标准库为主；如需请求 Open Food Facts，用 urllib，不要强制第三方依赖。完成后项目应能直接 `python3 -m diet_mvp plan ...` 跑通，并带测试。

## 产品范围
1. BMI（WHO 成人分级）
2. 按公开标准给参考热量（IOM 2005）和宏量营养素目标（WHO TRS 916 / OpenNutriTracker 默认占比）
3. 按热量和宏量目标推荐一日四餐食物搭配

## BMI / 参考热量模块（给 deepseek bot 的接口，必须稳定）

把**唯一实现入口**放在 `src/diet_mvp/nutrition/bmi_energy.py`。
类型与枚举放在 `src/diet_mvp/nutrition/interfaces.py`，bmi_energy 只实现函数，不改签名。

现在先写一套**可运行的对照实现**（公式必须按下述 OpenNutriTracker wiki 精确实现，含下面的数值例子测试）。在文件头用中文注释标明：

```
TEMPORARY REFERENCE IMPLEMENTATION
@deepseek bot：请替换本文件中的函数体，保持 interfaces.py 的类型与下面两个函数签名不变。
测试：tests/test_nutrition_contract.py 必须继续通过。
```

### 必须导出的函数

```python
def calculate_bmi(weight_kg: float, height_cm: float) -> BMIResult: ...
def calculate_reference_energy(profile: PersonProfile) -> EnergyResult: ...
```

校验：
- weight_kg > 0，height_cm > 0，否则 ValueError
- age_years 必须是 >= 13 的整数，否则 ValueError（与 OpenNutriTracker 一致：接受 13+，但公式是 19+ 成人方程；age < 19 时仍计算，同时在 EnergyResult.age_notice 里用中文说明“当前使用 19 岁及以上成人参考公式”）

### 公式（必须与 OpenNutriTracker Calculations wiki 一致）

BMI：
`BMI = weight_kg / (height_m ** 2)`，保留 1 位小数（round half away from 0 或常规 round 到 1 位即可，测试用 65kg / 1.68m → 23.0）。

WHO 成人分级（含边界）：
- < 18.5 underweight 偏瘦
- 18.5–24.9 normal 正常
- 25.0–29.9 pre_obesity 超重（前期肥胖）
- 30.0–34.9 obesity_class_i 肥胖 I 级
- 35.0–39.9 obesity_class_ii 肥胖 II 级
- ≥ 40.0 obesity_class_iii 肥胖 III 级

边界：18.5 → normal，25.0 → pre_obesity，30.0 → obesity_class_i，以此类推。

TDEE：IOM 2005 DRI p.204（正常/超重/肥胖成人 19+ 方程；注意括号：PA 同时乘体重项和身高项）。

男：
`TDEE = 864 - 9.72 * age + PA * (14.2 * weight_kg + 503 * height_m)`

女：
`TDEE = 387 - 7.31 * age + PA * (10.9 * weight_kg + 660.7 * height_m)`

PA 系数（IOM 2005 p.204）：

| activity     | PAL代表 | PA male | PA female |
|--------------|---------|---------|-----------|
| sedentary    | 1.25    | 1.00    | 1.00      |
| low_active   | 1.50    | 1.12    | 1.14      |
| active       | 1.75    | 1.27    | 1.27      |
| very_active  | 2.20    | 1.54    | 1.45      |

Sex：
- male → 男公式 + 男 PA
- female → 女公式 + 女 PA
- non_binary + calories_profile：
  - averaged（默认）：(男公式结果 + 女公式结果) / 2，各自用自己的 PA
  - estrogen_typical → 女公式
  - testosterone_typical → 男公式

日目标热量：
`daily_goal_kcal = TDEE + weight_goal_adjustment`
- maintain: 0
- lose: -500
- gain: +500
（MVP 不做每周速率和 target taper。）

低热量提示（不钳制目标，只打标）：
- 男或 testosterone_typical：daily_goal < 1500 → warning
- 女、estrogen_typical、或 non_binary averaged：daily_goal < 1200 → warning
恰好等于阈值不警告。

宏量目标（默认点值，来自 OpenNutriTracker，能量密度 WHO）：
- 碳水 60%，4 kcal/g
- 脂肪 25%，9 kcal/g
- 蛋白质 15%，4 kcal/g
`grams = daily_goal_kcal * share / density`

同时给出 WHO TRS 916（2003）人群范围，供配餐约束使用：
- 碳水 55–75%
- 脂肪 15–30%
- 蛋白质 10–15%

### 对照例子（必须写成测试）

女性，28 岁，65 kg，168 cm，low_active，maintain：
```
TDEE = 387 - 7.31*28 + 1.14*(10.9*65 + 660.7*1.68)
     = 387 - 204.68 + 1.14*1818.476
     ≈ 2255.38 kcal/day
```
测试允许 TDEE 与 2255 相差不超过 1 kcal。BMI 应为 23.0，category=normal。
宏量按 daily_goal（此处=TDEE）计算。

再测：男性 30 岁 80 kg 175 cm sedentary 的可复现计算（在测试里先手算期望值，允许 1 kcal 误差）。

## interfaces.py 建议形状（可微调字段，但函数名与核心字段不要改）

```python
class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"

class CaloriesProfile(str, Enum):
    AVERAGED = "averaged"
    ESTROGEN_TYPICAL = "estrogen_typical"
    TESTOSTERONE_TYPICAL = "testosterone_typical"

class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LOW_ACTIVE = "low_active"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"

class BMICategory(str, Enum):
    UNDERWEIGHT = "underweight"
    NORMAL = "normal"
    PRE_OBESITY = "pre_obesity"
    OBESITY_CLASS_I = "obesity_class_i"
    OBESITY_CLASS_II = "obesity_class_ii"
    OBESITY_CLASS_III = "obesity_class_iii"

class WeightGoal(str, Enum):
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"

@dataclass(frozen=True)
class PersonProfile:
    sex: Sex
    age_years: int
    height_cm: float
    weight_kg: float
    activity: ActivityLevel
    calories_profile: CaloriesProfile = CaloriesProfile.AVERAGED
    weight_goal: WeightGoal = WeightGoal.MAINTAIN

@dataclass(frozen=True)
class BMIResult:
    bmi: float
    category: BMICategory
    category_label_zh: str
    standard: str  # "WHO adult BMI"
    notes: str

@dataclass(frozen=True)
class MacroTarget:
    carbs_g: float
    fat_g: float
    protein_g: float
    carbs_pct: float  # 0.60
    fat_pct: float    # 0.25
    protein_pct: float  # 0.15

@dataclass(frozen=True)
class EnergyResult:
    tdee_kcal: float
    daily_goal_kcal: float
    weight_goal_adjustment_kcal: float
    pa_coefficient: float  # 实际代入公式的 PA；averaged 时可以放两性 PA 的均值，并在 notes 说明
    macros: MacroTarget
    protein_pct_range: tuple[float, float]  # (0.10, 0.15)
    fat_pct_range: tuple[float, float]      # (0.15, 0.30)
    carb_pct_range: tuple[float, float]     # (0.55, 0.75)
    standard_energy: str  # IOM 2005 DRI p.204
    standard_macros: str  # WHO TRS 916 + OpenNutriTracker 60/25/15
    age_notice: str | None
    low_calorie_warning: bool
    notes: str
```

再写一份给同事看的 `INTERFACE.md`（中文），写清模块路径、函数签名、输入输出、校验、公式、对照例子、以及 deepseek 只需改 `bmi_energy.py`。

## 食物库

- `data/sample_foods.json`：约 28–36 种常见食物，每项含 id、中文名、英文名、food_group（staple/protein/vegetable/fruit/dairy/fat/other）、per_100g 的 kcal、protein_g、fat_g、carbs_g、source。
- 数值用 USDA FoodData Central 风格的通用公开值（USDA 数据公有领域），source 写成食物名 + “USDA-style generic public values for offline demo”。**禁止**使用《中国食物成分表》或来源不明的转写数据。
- 覆盖主食、蛋白质、蔬菜、水果、乳制品、油脂，保证能配出一日三餐+加餐。
- `src/diet_mvp/foods/catalog.py`：加载本地 JSON。
- `src/diet_mvp/foods/off_client.py`：可选 Open Food Facts 搜索（`https://world.openfoodfacts.org/cgi/search.pl` 或 API v2），解析 per 100g 的 energy-kcal / proteins / fat / carbohydrates。网络失败时静默回退本地库。不要要求 API key。CLI 默认用本地库，加 `--use-off 关键词` 时才联网补充。

## 配餐核心（自写，思路参考 mcfit-meal-planner 的约束求解，不要复制其麦当劳代码/数据）

`src/diet_mvp/planner/recommender.py`：

输入：EnergyResult + 食物目录；输出一日计划。

餐次默认份额（OpenNutriTracker）：早餐 30%、午餐 40%、晚餐 20%、加餐 10%。

算法要求：
- 纯标准库。对每个餐次从不同食物组选 1–3 种食物并分配克数（建议 50g 步进，或 50–400g 合理范围；油脂更小，如 5–20g）。
- 约束：整日热量在 daily_goal_kcal ±10% 内；蛋白质/脂肪/碳水尽量落在 TRS 916 百分比范围内，并靠近 15/25/60 点目标。
- 多样性：四餐尽量不重复同一主食和同一蛋白质；每餐尽量包含蛋白质或乳制品 + 主食或水果，正餐再加蔬菜。
- 若穷举太大，用启发式：先按餐次热量目标贪心选菜，再局部交换/调整克数满足约束。可返回 1 个主方案；如果很容易再给最多 2 个备选。
- 输出结构要清晰：每餐食物、克数、kcal 与宏量；整日合计与目标对比；达不到约束时说明原因并仍给最接近方案。

## CLI

包路径：把 `src` 加到可导入路径（`python3 -m diet_mvp` 即可，或提供根目录的 `__main__`）。

```
python3 -m diet_mvp plan \
  --sex female --age 28 --height-cm 168 --weight-kg 65 \
  --activity low_active --goal maintain
```

中文打印：BMI 与分级、TDEE、日目标、宏量目标、四餐搭配、合计 vs 目标。加 `--json` 输出结构化 JSON。`--help` 可用。

再提供一个简短 `README.md`（中文）：怎么跑、公式出处、数据说明、接口留给 deepseek 的方式、免责声明（群体水平估计，非医疗建议）。

## 测试

`python3 -m unittest discover -s tests -v`
至少包括：
- BMI 边界与对照例子
- 女性 28y 对照 TDEE ≈ 2255
- lose/gain 调整 ±500
- 低热量 warning 逻辑
- non_binary averaged 是两性公式均值
- 配餐：用对照人物跑一次，热量在 ±10%，四餐都有食物
- 非法输入抛 ValueError

## 工程约束
- 不要 git init，除非已经在 git 里。
- 不要添加无用的大依赖、不要生成虚拟环境、不要调用付费 API。
- 代码注释和 README/INTERFACE 用中文。
- 写完后在仓库根打印文件树，并自己跑一遍 unittest 和一次 CLI demo，把命令与关键输出写到 `RUN_LOG.md`。
