"""跨模块稳定契约，替换计算实现时保持这些类型和字段不变。"""

from dataclasses import dataclass
from enum import Enum


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
    standard: str
    notes: str


@dataclass(frozen=True)
class MacroTarget:
    carbs_g: float
    fat_g: float
    protein_g: float
    carbs_pct: float
    fat_pct: float
    protein_pct: float


@dataclass(frozen=True)
class EnergyResult:
    tdee_kcal: float
    daily_goal_kcal: float
    weight_goal_adjustment_kcal: float
    pa_coefficient: float
    macros: MacroTarget
    protein_pct_range: tuple[float, float]
    fat_pct_range: tuple[float, float]
    carb_pct_range: tuple[float, float]
    standard_energy: str
    standard_macros: str
    age_notice: str | None
    low_calorie_warning: bool
    notes: str
