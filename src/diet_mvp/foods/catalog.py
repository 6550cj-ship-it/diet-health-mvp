"""读取并校验按每 100 克可食部分记录的演示食物。"""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

FOOD_GROUPS = {"staple", "protein", "vegetable", "fruit", "dairy", "fat", "other"}


@dataclass(frozen=True)
class Nutrients:
    kcal: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0

    def __post_init__(self):
        for value in (self.kcal, self.protein_g, self.fat_g, self.carbs_g):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("营养数值必须是非负有限数")

    def scaled(self, factor: float) -> "Nutrients":
        return Nutrients(self.kcal * factor, self.protein_g * factor,
                         self.fat_g * factor, self.carbs_g * factor)


def sum_nutrients(values: Iterable[Nutrients]) -> Nutrients:
    values = list(values)
    return Nutrients(*(sum(getattr(value, field) for value in values)
                       for field in ("kcal", "protein_g", "fat_g", "carbs_g")))


@dataclass(frozen=True)
class Food:
    id: str
    name_zh: str
    name_en: str
    food_group: str
    per_100g: Nutrients
    source: str

    def __post_init__(self):
        if not all(isinstance(v, str) and v.strip() for v in
                   (self.id, self.name_zh, self.name_en, self.source)):
            raise ValueError("食物 ID、名称和来源必须为非空文本")
        if self.food_group not in FOOD_GROUPS:
            raise ValueError("食物组无效")
        if not isinstance(self.per_100g, Nutrients) or self.per_100g.kcal <= 0:
            raise ValueError("食物必须包含有效的每 100 克营养及正热量")
        # 每 100 g 的物理量上限，避免错误的远程数据进入搜索。
        if self.per_100g.kcal > 1000 or any(value > 100 for value in
                (self.per_100g.protein_g, self.per_100g.fat_g, self.per_100g.carbs_g)):
            raise ValueError("每 100 克热量不得超过 1000 kcal，单项宏量不得超过 100 g")


def load_catalog(path: str | Path | None = None) -> list[Food]:
    path = Path(path) if path is not None else Path(__file__).resolve().parents[3] / "data" / "sample_foods.json"
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or not rows:
            raise ValueError("目录必须是非空列表")
        foods = [Food(id=row["id"], name_zh=row["name_zh"], name_en=row["name_en"],
                      food_group=row["food_group"], per_100g=Nutrients(**row["per_100g"]),
                      source=row["source"]) for row in rows]
        if len({food.id for food in foods}) != len(foods):
            raise ValueError("食物 ID 不可重复")
        return foods
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise ValueError(f"无法加载食物目录 {path}，{exc}") from exc
