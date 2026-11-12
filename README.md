# 饮食健康 MVP

Python 3.11+，仅使用标准库。在仓库根直接运行，无需安装依赖或创建虚拟环境。

```bash
python3 -m diet_mvp plan \
  --sex female --age 28 --height-cm 168 --weight-kg 65 \
  --activity low_active --goal maintain

python3 -m diet_mvp plan \
  --sex female --age 28 --height-cm 168 --weight-kg 65 \
  --activity low_active --goal maintain --json

python3 -m unittest discover -s tests -v
python3 -m diet_mvp plan --help
```

`--goal` 支持 `maintain`、`lose`、`gain`。`--sex non_binary` 可结合 `--calories-profile averaged|estrogen_typical|testosterone_typical` 使用。默认全程离线，只有显式添加 `--use-off 酸奶` 才通过 urllib 搜索 Open Food Facts，失败时静默保留离线目录。搜索只发送关键词，不发送身高、体重等个人资料。

## 公式与接口

唯一公式实现位于 `src/diet_mvp/nutrition/bmi_energy.py`，固定类型位于 `interfaces.py`。给 deepseek 的替换说明、签名和数值例子见 [INTERFACE.md](INTERFACE.md)。替换后必须继续通过 `tests/test_nutrition_contract.py`。

计算按 [OpenNutriTracker Calculations wiki](https://github.com/simonoppowa/OpenNutriTracker/wiki/Calculations) 的明确公式实现。参考热量对应 [IOM 2005 DRI，p.204，DOI 10.17226/10490](https://doi.org/10.17226/10490)，PA 同时乘体重项和身高项。BMI 使用 WHO 成人阈值，按原值分级，仅显示值舍入。日目标在参考热量上加 0 或正负 500 kcal，低热量只提示，不修改结果。

宏量点目标 60% 碳水、25% 脂肪、15% 蛋白质是 OpenNutriTracker 产品默认值。配餐范围来自任务指定的 [WHO/FAO TRS 916](https://www.who.int/publications/i/item/924120916X)，碳水 55–75%、脂肪 15–30%、蛋白质 10–15%。这些历史人群范围和产品默认值并非个体处方，也不表示已对更新指南完成综述。

## 食物与配餐

`data/sample_foods.json` 含 34 种常见食物，按每 100 g 可食部分记录。名称标明熟重、干重、去皮或沥干状态。值为手工整理的 USDA 风格通用演示值，来源字段明确标记 `USDA-style generic public values for offline demo`，不声称逐条对应某个 FDC 记录或实验测定。未使用《中国食物成分表》。[USDA FoodData Central](https://fdc.nal.usda.gov/api-guide/) 数据属于公有领域。

OFF 商品单独标注来源和 ODbL，缺少任一必要营养字段时跳过，不把缺失值补成 0。每 100 g 热量大于 1000 kcal 或单项宏量大于 100 g 时拒绝入库。具体请求和字段说明见 [OFF API 官方文档](https://openfoodfacts.github.io/openfoodfacts-server/api/tutorial-off-api/)。未知类别归 `other`，因此补充成功的商品不一定入选。

四餐热量参考份额为 30%、40%、20%、10%。算法先按不同食物组生成每餐 1–3 种食物的离散候选，再以宽度 64 的束搜索平衡全天热量、宏量目标及主食和蛋白质食物多样性。没有复制现成应用、代码或品牌食物数据。普通食物以 50 g 为步进且不超过 400 g，油脂与坚果为 5–20 g。干燕麦、面包、蛋白质和蔬果采用更低份量上限。

早餐优先主食、乳制品或蛋白质、水果。午餐及晚餐优先加入蔬菜。加餐可包含水果、乳制品和少量油脂或坚果。目录不足时放宽食物组偏好，并说明缺项。仅返回一个主方案，启发式搜索不保证全局最优。

`energy_within_tolerance` 表示全天热量在目标正负 10% 内。`macro_ranges_met` 表示三项供能比都在范围内，`constraints_met` 为两者同时满足。食物组、多样性是软偏好，未满足会另列 `warnings`。未找到达标方案时仍返回搜索保留方案中的最接近方案，并说明限制，不能据此证明不存在其他可行方案。

实际供能比使用宏量克数乘 4/9/4，再除以食物库合计 kcal。食品专用能量系数、纤维和舍入可造成三项比例之和不为 100%，程序不会强行归一化。食物克数、营养和来源均可在 JSON 中核查，显示舍入不影响内部约束检查。

## 适用边界

这是群体水平估计和离线配餐演示，非医疗建议。成人 BMI 分级不能用于未成年人诊断。接受 13–18 岁只为保持指定接口行为，会明确提示使用成人方程。非二元 averaged 是两性公式结果均值的产品约定，未经个体有效性验证。低热量标记和营养比例达标都不代表方案安全或营养完整。

本项目未评估过敏、疾病、孕哺期、药物、微量营养素、钠、纤维、价格、口味和烹调过程。非正日目标保留原公式结果，但不生成可食用配餐。

真实执行命令、输出及文件树见 [RUN_LOG.md](RUN_LOG.md)。

## 数据来源与许可

- 当前离线食物库 `data/sample_foods.json` 是按 USDA FoodData Central 风格整理的通用公开值，只作演示用。USDA FoodData Central 采用 CC0 许可。
- Open Food Facts 的数据库采用 ODbL 许可。正式接入后需要注明来源，从它衍生的数据库也必须以 ODbL 共享。
- 未使用《中国食物成分表》或任何未标明许可证的转写数据。
