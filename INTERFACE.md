# BMI 与参考热量稳定接口

## 替换范围

唯一计算入口为 `src/diet_mvp/nutrition/bmi_energy.py`，类型和枚举为 `src/diet_mvp/nutrition/interfaces.py`。CLI 和配餐器直接消费这些类型，不包含第二份 BMI 或热量方程。

当前文件是可运行的临时对照实现。deepseek 只需替换 `bmi_energy.py` 的函数体，保持 `interfaces.py` 和两个公开签名不变，不新增依赖。测试命令如下。

```bash
python3 -m unittest discover -s tests -p test_nutrition_contract.py -v
python3 -m unittest discover -s tests -v
```

根目录 `diet_mvp/__init__.py` 只把 `src/diet_mvp` 纳入包路径，所以在根目录无需安装即可导入。

```python
from diet_mvp.nutrition.bmi_energy import calculate_bmi, calculate_reference_energy
from diet_mvp.nutrition.interfaces import ActivityLevel, PersonProfile, Sex

def calculate_bmi(weight_kg: float, height_cm: float) -> BMIResult: ...
def calculate_reference_energy(profile: PersonProfile) -> EnergyResult: ...

profile = PersonProfile(
    sex=Sex.FEMALE, age_years=28, height_cm=168, weight_kg=65,
    activity=ActivityLevel.LOW_ACTIVE,
)
bmi = calculate_bmi(profile.weight_kg, profile.height_cm)
energy = calculate_reference_energy(profile)
```

## 输入

`PersonProfile` 是 frozen dataclass，不会被计算函数修改。

| 字段 | 类型及允许值 | 默认 |
| --- | --- | --- |
| sex | Sex，male / female / non_binary | 必填 |
| age_years | int，至少 13，不接受 bool 或 28.0 | 必填 |
| height_cm | 有限正数，厘米 | 必填 |
| weight_kg | 有限正数，公斤 | 必填 |
| activity | ActivityLevel，sedentary / low_active / active / very_active | 必填 |
| calories_profile | CaloriesProfile，averaged / estrogen_typical / testosterone_typical | averaged |
| weight_goal | WeightGoal，lose / maintain / gain | maintain |

调用方应传对应枚举。临时实现也接受枚举的同值字符串，无效值抛 `ValueError`。非二元用户的 calories_profile 决定参考方程，male/female 按 sex 选方程，忽略其他有效 calories_profile 值。类型构造器只保存数据，实际输入校验在计算函数完成。

两个函数均要求身高、体重大于 0，拒绝非数值、bool、NaN、无穷及不能进行有限运算的极端数值，抛 `ValueError`。参考热量函数另校验整数年龄和枚举。年龄 13–18 岁仍计算，在 `age_notice` 中包含“当前使用 19 岁及以上成人参考公式”。19 岁及以上为 `None`。未强加任务未指定的年龄上限。

## BMI 输出与边界

```text
height_m = height_cm / 100
BMI = weight_kg / height_m**2
```

先用未舍入值确定分级，再用 `round(BMI, 1)` 产生显示值。因此原值 24.99 显示 25.0 时，category 仍为 normal。需要判断分级的调用方应读 category。

| 原始 BMI | category | category_label_zh |
| --- | --- | --- |
| 小于 18.5 | underweight | 偏瘦 |
| 18.5 至小于 25 | normal | 正常 |
| 25 至小于 30 | pre_obesity | 超重（前期肥胖） |
| 30 至小于 35 | obesity_class_i | 肥胖 I 级 |
| 35 至小于 40 | obesity_class_ii | 肥胖 II 级 |
| 40 及以上 | obesity_class_iii | 肥胖 III 级 |

`BMIResult` 包含 `bmi: float`、`category: BMICategory`、`category_label_zh: str`、`standard: str` 和 `notes: str`。standard 固定为 `WHO adult BMI`。notes 说明成人筛查适用性和舍入规则。此函数无年龄输入，因此不能自行判断是否适合未成年人。

## 参考热量方程

按任务指定的 [OpenNutriTracker wiki](https://github.com/simonoppowa/OpenNutriTracker/wiki/Calculations)，使用 [IOM 2005 DRI](https://doi.org/10.17226/10490) p.204 方程。代码不根据 BMI 切换方程。PA 乘括号内体重项与身高项之和，不得只乘体重项。

```text
male = 864 - 9.72 * age + PA_male * (14.2 * weight_kg + 503 * height_m)
female = 387 - 7.31 * age + PA_female * (10.9 * weight_kg + 660.7 * height_m)
```

| activity | 代表 PAL | 男 PA | 女 PA |
| --- | --- | --- | --- |
| sedentary | 1.25 | 1.00 | 1.00 |
| low_active | 1.50 | 1.12 | 1.14 |
| active | 1.75 | 1.27 | 1.27 |
| very_active | 2.20 | 1.54 | 1.45 |

代表 PAL 是应用所选的区间代表值，不是直接代入上述方程的 PA，也不再另乘 TDEE。

male 使用男公式，female 使用女公式。non_binary 的 averaged 分别使用两性 PA 计算后取结果均值，estrogen_typical 使用女公式，testosterone_typical 使用男公式。averaged 的 `pa_coefficient` 保存 PA 均值，仅供说明，不能将此均值代入一个公式重建 averaged 结果，notes 会写明两个实际系数。

```text
maintain adjustment = 0 kcal
lose adjustment = -500 kcal
gain adjustment = +500 kcal
daily_goal_kcal = tdee_kcal + adjustment
```

不实现每周速率、target taper、手动偏移或运动热量追加。

低热量只打标，不钳制目标。male 或 non_binary testosterone_typical 使用 1500 kcal 阈值。female、non_binary estrogen_typical 和 averaged 使用 1200 kcal 阈值。严格小于才警告，恰好相等不警告。该阈值是指定产品行为，不是 WHO TRS 916 的营养充分性判据。

## 宏量目标及输出字段

```text
carbs_g = daily_goal_kcal * 0.60 / 4
fat_g = daily_goal_kcal * 0.25 / 9
protein_g = daily_goal_kcal * 0.15 / 4
```

`MacroTarget` 包含上述三个克数字段和 `carbs_pct=0.60`、`fat_pct=0.25`、`protein_pct=0.15`。百分比字段均使用 0–1 的比例。

`EnergyResult` 是 frozen dataclass，不对热量和克数做显示舍入。

| 字段 | 含义 |
| --- | --- |
| tdee_kcal | 公式估计的每日总能量消耗 |
| daily_goal_kcal | 调整体重目标后的日热量 |
| weight_goal_adjustment_kcal | 0、-500 或 +500 |
| pa_coefficient | 本次 PA；averaged 时为 PA 均值 |
| macros | MacroTarget，以 daily_goal 计算 |
| protein_pct_range | (0.10, 0.15) |
| fat_pct_range | (0.15, 0.30) |
| carb_pct_range | (0.55, 0.75) |
| standard_energy | IOM 2005 DRI p.204 |
| standard_macros | WHO TRS 916 + OpenNutriTracker 60/25/15 |
| age_notice | 13–18 岁中文提示，其他为 None |
| low_calorie_warning | 严格低于阈值时为 True |
| notes | 估计性质、averaged 系数说明、特殊结果提示 |

范围来自任务指定的 [WHO/FAO TRS 916](https://www.who.int/publications/i/item/924120916X) 人群目标，点值来自应用默认配置，不可混为同一来源。函数保留有限的非正日目标及对应公式克数，并打低热量标记。此类结果不能作为摄入建议，配餐器会返回无食物的四餐结构和明确原因。

## 对照例子

女性 28 岁、65 kg、168 cm、low_active、maintain。

```text
BMI = 65 / 1.68**2 = 23.030...，显示 23.0，normal
TDEE = 387 - 7.31*28 + 1.14*(10.9*65 + 660.7*1.68)
     = 182.32 + 1.14*1818.476
     = 2255.38264 kcal/日
碳水 338.307396 g
脂肪 62.64951778 g
蛋白质 84.576849 g
```

男性 30 岁、80 kg、175 cm、sedentary、maintain。

```text
TDEE = 864 - 9.72*30 + 1.00*(14.2*80 + 503*1.75)
     = 572.4 + 2016.25
     = 2588.65 kcal/日
```

测试同时覆盖 BMI 全部分级边界、四档 PA、正负 500 调整、低热量两侧及相等边界、三种非二元参考方式、年龄提示和非法输入。

## 配餐与 CLI 消费约定

`recommend_day(energy: EnergyResult, catalog: list[Food]) -> DailyPlan` 位于 `src/diet_mvp/planner/recommender.py`。结果包含 meals、totals、target_kcal、target_macros、macro_percentages、macro_ranges、热量偏差、达标标记及 warnings。每个餐次包含目标热量、食物份量和营养合计，每种食物份量包含来源。

`constraints_met` 只表示日热量和三个宏量范围同时满足，多样性及食物组缺项单独报告。CLI 的 JSON 顶层键为 `profile`、`bmi`、`energy`、`plan`、`catalog`、`disclaimer`。枚举输出字符串，元组输出数组，None 输出 null。默认 CLI 不联网，`--use-off` 才搜索商品。
