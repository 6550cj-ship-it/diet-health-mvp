"""BMI 与参考热量计算入口，严格遵循 INTERFACE.md 的稳定契约。"""

import math

from .interfaces import (
    ActivityLevel,
    BMICategory,
    BMIResult,
    CaloriesProfile,
    EnergyResult,
    MacroTarget,
    PersonProfile,
    Sex,
    WeightGoal,
)

__all__ = ["calculate_bmi", "calculate_reference_energy"]


# BMI 分级：上界为开区间，最后一项兜底。
_BMI_CATEGORIES = (
    (18.5, BMICategory.UNDERWEIGHT, "偏瘦"),
    (25.0, BMICategory.NORMAL, "正常"),
    (30.0, BMICategory.PRE_OBESITY, "超重（前期肥胖）"),
    (35.0, BMICategory.OBESITY_CLASS_I, "肥胖 I 级"),
    (40.0, BMICategory.OBESITY_CLASS_II, "肥胖 II 级"),
    (math.inf, BMICategory.OBESITY_CLASS_III, "肥胖 III 级"),
)

_BMI_STANDARD = "WHO adult BMI"
_BMI_NOTES = (
    "分级采用未舍入 BMI；显示值用 round(BMI, 1) 保留一位小数。"
    "WHO 成人 BMI 是群体筛查指标，不能区分肌肉与脂肪；"
    "本函数无年龄输入，不能自行判断是否适合未成年人，不用于未成年人分级诊断。"
)

# 活动等级对应的（男 PA，女 PA）；代表 PAL 不代入方程。
_PA_TABLE = {
    ActivityLevel.SEDENTARY: (1.00, 1.00),
    ActivityLevel.LOW_ACTIVE: (1.12, 1.14),
    ActivityLevel.ACTIVE: (1.27, 1.27),
    ActivityLevel.VERY_ACTIVE: (1.54, 1.45),
}

_WEIGHT_GOAL_ADJUSTMENTS = {
    WeightGoal.MAINTAIN: 0.0,
    WeightGoal.LOSE: -500.0,
    WeightGoal.GAIN: 500.0,
}

_PROTEIN_RANGE = (0.10, 0.15)
_FAT_RANGE = (0.15, 0.30)
_CARB_RANGE = (0.55, 0.75)
_CARB_PCT = 0.60
_FAT_PCT = 0.25
_PROTEIN_PCT = 0.15

_ENERGY_NOTES = (
    "群体水平估计，非个体能量消耗测量。"
    "未加运动热量或手动偏移，未做每周速率和目标体重渐减。"
)


def _positive_finite(value: object, name: str) -> float:
    """校验为正的有限数值，并统一返回 float。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} 必须是大于 0 的有限数值")
    try:
        numeric = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是大于 0 的有限数值") from exc
    if not math.isfinite(numeric) or numeric <= 0.0:
        raise ValueError(f"{name} 必须是大于 0 的有限数值")
    return numeric


def _coerce_enum(enum_type, value: object, name: str):
    """接受枚举或其同值字符串；无效值转为 ValueError。"""
    try:
        return enum_type(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} 无效") from exc


def _male_energy_kcal(age: int, weight_kg: float, height_m: float, pa: float) -> float:
    """IOM 2005 DRI p.204 男性参考方程。"""
    try:
        value = 864 - 9.72 * age + pa * (14.2 * weight_kg + 503 * height_m)
    except OverflowError as exc:
        raise ValueError("输入超出参考热量可计算范围") from exc
    if not math.isfinite(value):
        raise ValueError("输入超出参考热量可计算范围")
    return value


def _female_energy_kcal(age: int, weight_kg: float, height_m: float, pa: float) -> float:
    """IOM 2005 DRI p.204 女性参考方程。"""
    try:
        value = 387 - 7.31 * age + pa * (10.9 * weight_kg + 660.7 * height_m)
    except OverflowError as exc:
        raise ValueError("输入超出参考热量可计算范围") from exc
    if not math.isfinite(value):
        raise ValueError("输入超出参考热量可计算范围")
    return value


def calculate_bmi(weight_kg: float, height_cm: float) -> BMIResult:
    """计算 BMI，先按未舍入值分级，再产生一位显示值。"""
    weight = _positive_finite(weight_kg, "weight_kg")
    height = _positive_finite(height_cm, "height_cm")

    try:
        height_m = height / 100.0
        height_sq = height_m ** 2
    except OverflowError as exc:
        raise ValueError("身高体重超出可计算范围") from exc

    if not math.isfinite(height_sq) or height_sq <= 0.0:
        raise ValueError("身高体重超出可计算范围")

    try:
        raw_bmi = weight / height_sq
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("身高体重超出可计算范围") from exc

    if not math.isfinite(raw_bmi) or raw_bmi <= 0.0:
        raise ValueError("身高体重超出可计算范围")

    for upper, category, label in _BMI_CATEGORIES:
        if raw_bmi < upper:
            return BMIResult(
                bmi=round(raw_bmi, 1),
                category=category,
                category_label_zh=label,
                standard=_BMI_STANDARD,
                notes=_BMI_NOTES,
            )

    # raw_bmi 有限时不会到达这里。
    raise ValueError("BMI 无法计算")


def calculate_reference_energy(profile: PersonProfile) -> EnergyResult:
    """按 IOM 2005 DRI p.204 计算参考能量、宏量目标与提示。"""
    if not isinstance(profile, PersonProfile):
        raise ValueError("profile 必须是 PersonProfile")

    weight = _positive_finite(profile.weight_kg, "weight_kg")
    height = _positive_finite(profile.height_cm, "height_cm")

    if type(profile.age_years) is not int or profile.age_years < 13:
        raise ValueError("age_years 必须是大于等于 13 的整数")
    age = profile.age_years

    sex = _coerce_enum(Sex, profile.sex, "sex")
    activity = _coerce_enum(ActivityLevel, profile.activity, "activity")
    calories_profile = _coerce_enum(
        CaloriesProfile, profile.calories_profile, "calories_profile"
    )
    weight_goal = _coerce_enum(WeightGoal, profile.weight_goal, "weight_goal")

    pa_m, pa_f = _PA_TABLE[activity]
    height_m = height / 100.0
    notes = _ENERGY_NOTES

    if sex == Sex.MALE:
        tdee_kcal = _male_energy_kcal(age, weight, height_m, pa_m)
        pa_coefficient = pa_m
        low_threshold = 1500.0
    elif sex == Sex.FEMALE:
        tdee_kcal = _female_energy_kcal(age, weight, height_m, pa_f)
        pa_coefficient = pa_f
        low_threshold = 1200.0
    elif calories_profile == CaloriesProfile.TESTOSTERONE_TYPICAL:
        tdee_kcal = _male_energy_kcal(age, weight, height_m, pa_m)
        pa_coefficient = pa_m
        low_threshold = 1500.0
    elif calories_profile == CaloriesProfile.ESTROGEN_TYPICAL:
        tdee_kcal = _female_energy_kcal(age, weight, height_m, pa_f)
        pa_coefficient = pa_f
        low_threshold = 1200.0
    else:
        male_kcal = _male_energy_kcal(age, weight, height_m, pa_m)
        female_kcal = _female_energy_kcal(age, weight, height_m, pa_f)
        tdee_kcal = male_kcal / 2 + female_kcal / 2
        pa_coefficient = (pa_m + pa_f) / 2
        low_threshold = 1200.0
        notes += (
            f" 两性公式分别使用 PA {pa_m:g} 和 {pa_f:g} 后取结果均值；"
            "pa_coefficient 仅记录 PA 均值，不能用来重算单一公式。"
            "此均值是产品约定，未经个体有效性验证。"
        )

    adjustment = _WEIGHT_GOAL_ADJUSTMENTS[weight_goal]
    daily_goal = tdee_kcal + adjustment
    if not math.isfinite(daily_goal):
        raise ValueError("输入超出参考热量可计算范围")

    low_calorie_warning = daily_goal < low_threshold
    if daily_goal <= 0.0:
        notes += " 计算得到非正日目标（低热量结果），保留原公式结果，不应据此安排摄入。"
    elif low_calorie_warning:
        notes += " 日目标低于产品低热量阈值，仅作标记，未钳制目标；结果不应作为摄入建议。"

    macros = MacroTarget(
        carbs_g=daily_goal * _CARB_PCT / 4,
        fat_g=daily_goal * _FAT_PCT / 9,
        protein_g=daily_goal * _PROTEIN_PCT / 4,
        carbs_pct=_CARB_PCT,
        fat_pct=_FAT_PCT,
        protein_pct=_PROTEIN_PCT,
    )

    age_notice = (
        "当前使用 19 岁及以上成人参考公式。13–18 岁结果不能代替生长发育期营养评估。"
        if age < 19
        else None
    )

    return EnergyResult(
        tdee_kcal=tdee_kcal,
        daily_goal_kcal=daily_goal,
        weight_goal_adjustment_kcal=adjustment,
        pa_coefficient=pa_coefficient,
        macros=macros,
        protein_pct_range=_PROTEIN_RANGE,
        fat_pct_range=_FAT_RANGE,
        carb_pct_range=_CARB_RANGE,
        standard_energy="IOM 2005 DRI p.204",
        standard_macros="WHO TRS 916 + OpenNutriTracker 60/25/15",
        age_notice=age_notice,
        low_calorie_warning=low_calorie_warning,
        notes=notes,
    )
