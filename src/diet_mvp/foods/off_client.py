"""可选的公开商品搜索，仅传送搜索词，不传送个人资料。"""

import json
from http.client import HTTPException
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .catalog import Food, Nutrients


def _group(product: dict) -> str:
    tags = product.get("categories_tags", [])
    if not isinstance(tags, list):
        return "other"
    # 只识别较明确的类别；复合菜品或不明类别归入 other。
    tag_set = {tag for tag in tags if isinstance(tag, str)}
    matches = []
    for group, candidates in [
        ("dairy", {"en:milks", "en:yogurts", "en:cheeses"}),
        ("fat", {"en:olive-oils", "en:vegetable-oils", "en:nuts"}),
        ("protein", {"en:eggs", "en:meats", "en:fishes", "en:tofus", "en:legumes"}),
        ("staple", {"en:rices", "en:pastas", "en:breads", "en:oat-flakes"}),
        ("fruit", {"en:fruits", "en:fresh-fruits"}),
        ("vegetable", {"en:vegetables", "en:fresh-vegetables"}),
    ]:
        if candidates.intersection(tag_set):
            matches.append(group)
    return matches[0] if len(matches) == 1 else "other"


def search_foods(query: str, *, timeout: float = 3.0, limit: int = 8) -> list[Food]:
    """网络、格式或字段错误时返回空列表，由调用方保留本地目录。"""
    if not isinstance(query, str) or not query.strip():
        return []
    params = urlencode({"search_terms": query.strip(), "search_simple": 1,
                        "action": "process", "json": 1, "page_size": min(max(limit, 1), 20),
                        "fields": "code,product_name,product_name_zh,product_name_en,categories_tags,nutriments"})
    request = Request("https://world.openfoodfacts.org/cgi/search.pl?" + params,
                      headers={"User-Agent": "diet-health-mvp/0.1 (local offline-demo; Python urllib)",
                               "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            return []
        payload = json.loads(raw)
        products = payload.get("products", []) if isinstance(payload, dict) else []
        if not isinstance(products, list):
            return []
        foods = {}
        for product in products[:20]:
            if not isinstance(product, dict):
                continue
            try:
                code = product["code"]
                name = product.get("product_name") or product.get("product_name_en") or product.get("product_name_zh")
                if not isinstance(code, str) or not code.strip() or not isinstance(name, str):
                    continue
                nutriments = product["nutriments"]
                values = [nutriments[key] for key in ("energy-kcal_100g", "proteins_100g", "fat_100g", "carbohydrates_100g")]
                if any(isinstance(value, bool) for value in values):
                    continue
                nutrients = Nutrients(*(float(value) for value in values))
                food = Food("off_" + code, product.get("product_name_zh") or name,
                            product.get("product_name_en") or name, _group(product), nutrients,
                            f"Open Food Facts https://world.openfoodfacts.org/product/{code} (ODbL)")
                foods[food.id] = food
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
        return list(foods.values())[:limit]
    except (OSError, ValueError, UnicodeError, HTTPException):
        return []


def supplement_catalog(local_foods: list[Food], query: str) -> list[Food]:
    """只追加成功解析且 ID 不重复的商品，始终保留本地食物。"""
    known = {food.id for food in local_foods}
    return list(local_foods) + [food for food in search_foods(query) if food.id not in known]
