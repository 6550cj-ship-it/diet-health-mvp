"""允许在仓库根直接运行，业务实现统一放在 src/diet_mvp。"""

from pathlib import Path

__path__.append(str(Path(__file__).resolve().parent.parent / "src" / "diet_mvp"))
