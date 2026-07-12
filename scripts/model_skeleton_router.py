#!/usr/bin/env python3
"""Route a modeling problem to a competition-oriented model skeleton.

Reads `06_过程记录/problem_analysis.md`, infers one or more problem types, and
creates reviewable starter artifacts:

- `06_过程记录/model_skeleton/model_skeleton.json`
- `06_过程记录/model_skeleton/model_skeleton.md`
- optional starter code under `02_代码/generated_skeleton/`

The output is deliberately a skeleton, not a fake solution. Its job is to force
the first competition draft to contain variables, objective/metrics, constraints,
checker plan, validation plan, and report assets matched to the detected type.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

TYPE_RULES = {
    "optimization": {
        "label": "优化/资源配置类",
        "keywords": ["优化", "最优", "最大", "最小", "成本", "收益", "利润", "资源", "约束", "决策", "规划", "整数规划", "线性规划", "调度", "排产", "选址", "分配", "路径", "车辆", "TSP", "VRP"],
        "variables": ["x[i,j,t]：决策变量/分配量/选择量", "y[k]：0-1辅助变量", "s[t]：状态变量或库存/余量"],
        "model_core": ["明确目标函数：最大收益/最小成本/最小风险/多目标加权或 Pareto", "列出硬约束：容量、守恒、时间、逻辑、唯一性、上下界", "先做可行启发式，再做 LP/MIP/NLP 或滚动优化增强"],
        "checker": ["容量/面积/资源不超限", "逻辑约束是否违反", "所有必选对象是否覆盖", "目标函数可由结果表复算"],
        "validation": ["baseline 对比", "关键参数 ±5%/±10%/±20% 敏感性", "多情景/鲁棒性", "求解状态与 gap/可行性日志"],
    },
    "prediction": {
        "label": "预测/回归/时间序列类",
        "keywords": ["预测", "预报", "趋势", "回归", "时间序列", "未来", "估计", "误差", "训练", "测试", "ARIMA", "随机森林", "机器学习", "销量", "需求", "价格", "风险概率"],
        "variables": ["X：特征矩阵", "y：预测目标", "t：时间索引", "ŷ：预测值"],
        "model_core": ["划分训练/验证/测试或滚动回测", "建立 baseline：均值/移动平均/线性回归", "选择可解释模型 + 增强模型，并保留误差诊断"],
        "checker": ["时间穿越/数据泄漏检查", "训练测试主体或时间段隔离", "缺失值和异常值处理记录", "目标变量单位一致"],
        "validation": ["MAE/RMSE/MAPE/R2 或分类指标", "残差图与误差分布", "交叉验证/滚动验证", "特征重要性或系数解释"],
    },
    "evaluation": {
        "label": "综合评价/排序/指标体系类",
        "keywords": ["评价", "评估", "指标", "权重", "排序", "等级", "综合", "TOPSIS", "AHP", "熵权", "主成分", "因子分析", "打分", "排名", "优劣"],
        "variables": ["a[i,j]：对象 i 在指标 j 上的原始值", "w[j]：指标权重", "z[i,j]：标准化指标", "S[i]：综合得分"],
        "model_core": ["构造指标层级与正/逆/区间型方向", "客观权重/主观权重/组合权重", "TOPSIS/灰色综合/PCA 等排序模型"],
        "checker": ["指标方向是否统一", "权重和是否为 1", "标准化后范围是否合理", "排序对权重扰动是否稳定"],
        "validation": ["权重敏感性", "替代评价方法对比", "排序 Spearman/Kendall 稳定性", "异常指标剔除影响"],
    },
    "simulation": {
        "label": "仿真/随机情景/系统演化类",
        "keywords": ["仿真", "模拟", "Monte Carlo", "蒙特卡洛", "随机", "情景", "风险", "分布", "系统动力学", "排队", "Agent", "元胞", "不确定"],
        "variables": ["state[t]：系统状态", "u[t]：控制或外生输入", "ε：随机扰动", "K：仿真次数"],
        "model_core": ["定义状态转移或事件流程", "设定随机变量分布和参数来源", "固定 seed 并输出均值、分位数、CVaR/最坏情景"],
        "checker": ["随机种子可复现", "分布参数有来源", "样本量足够", "极端情景不违反物理/业务约束"],
        "validation": ["收敛性检查", "情景对比", "置信区间", "参数扰动和压力测试"],
    },
    "network_routing": {
        "label": "路径/网络/图/物流类",
        "keywords": ["路径", "路线", "网络", "节点", "边", "流量", "最短路", "最大流", "最小生成树", "物流", "配送", "车辆", "VRP", "TSP", "交通"],
        "variables": ["x[i,j,k]：车辆/流在边(i,j)上的选择", "q[k,t]：载重/流量", "arrive[i]：到达时间"],
        "model_core": ["图建模：节点、边、距离/时间/费用", "路径连续性、容量、时间窗、访问约束", "精确算法/启发式/局部搜索组合"],
        "checker": ["每个需求点访问次数", "车辆容量与时间窗", "路径连通无断链", "总距离/成本可复算"],
        "validation": ["与最近邻/贪心 baseline 对比", "需求扰动", "车辆数/容量敏感性", "路径可视化"],
    },
    "statistics": {
        "label": "统计检验/因果解释类",
        "keywords": ["显著", "检验", "相关", "因果", "影响因素", "方差", "置信", "假设检验", "相关性", "回归诊断", "异常判定", "分组差异"],
        "variables": ["H0/H1：原假设/备择假设", "β：回归系数", "p：显著性水平", "CI：置信区间"],
        "model_core": ["明确统计假设与样本独立性", "选择检验/回归/分层模型", "报告效应量而不只报告 p 值"],
        "checker": ["独立性/重复测量检查", "多重检验校正", "异常值影响", "变量共线性"],
        "validation": ["残差诊断", "稳健标准误或替代模型", "置信区间", "分层/亚组稳定性"],
    },
}

@dataclass
class RouteResult:
    type_id: str
    label: str
    score: int
    matched_keywords: list[str]
    confidence: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def normalize(text: str) -> str:
    return text.lower().replace("，", ",").replace("。", ".")


def route(text: str) -> list[RouteResult]:
    nt = normalize(text)
    results: list[RouteResult] = []
    for type_id, rule in TYPE_RULES.items():
        matched = []
        for kw in rule["keywords"]:
            if kw.lower() in nt:
                matched.append(kw)
        score = len(matched)
        if score:
            confidence = "high" if score >= 5 else "medium" if score >= 2 else "low"
            results.append(RouteResult(type_id, rule["label"], score, matched[:12], confidence))
    if not results:
        results.append(RouteResult("unknown", "未能可靠识别：需人工补充题型", 0, [], "low"))
    return sorted(results, key=lambda x: x.score, reverse=True)


def extract_questions(text: str) -> list[str]:
    questions: list[str] = []
    for line in text.splitlines():
        s = line.strip(" -\t")
        if not s:
            continue
        if re.match(r"^(Q\d+|问题\s*\d+|第[一二三四五六七八九十]+问|\d+[).、])", s, flags=re.I):
            questions.append(s[:240])
    return questions[:20]


def starter_code(primary: str) -> dict[str, str]:
    common = """from pathlib import Path\nimport json\n\nBASE = Path(__file__).resolve().parents[2]\nOUT = BASE / '03_结果表格'\nOUT.mkdir(exist_ok=True)\n\n"""
    checker = common + """# TODO: replace skeleton checks with domain-specific hard constraints.\nchecks = [\n    {'id': 'non_empty_results', 'status': 'warn', 'message': 'implement after model_main.py writes formal results'},\n]\nissue_count = sum(1 for c in checks if c['status'] == 'fail')\npath = OUT / 'domain_checker_results.json'\npath.write_text(json.dumps({'issue_count': issue_count, 'checks': checks}, ensure_ascii=False, indent=2), encoding='utf-8')\nprint(f'Wrote {path}; issue_count={issue_count}')\n"""
    sensitivity = common + """# TODO: perturb key parameters and compare objective/metrics.\nrows = [{'parameter': 'example_key_parameter', 'factor': f, 'metric': None, 'note': 'replace with real sensitivity result'} for f in [0.8, 0.9, 1.1, 1.2]]\npath = OUT / 'sensitivity_plan.json'\npath.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')\nprint(f'Wrote {path}')\n"""
    if primary == 'optimization':
        model = common + """# Optimization skeleton: define decision variables, objective, constraints, then solve.\n# Recommended path: feasible heuristic first -> LP/MIP/NLP solver -> constraint checker.\nresult = {\n    'model_type': 'optimization',\n    'solver_status': 'skeleton_not_solved',\n    'objective': None,\n    'decision_variables': [],\n    'constraints_to_implement': ['capacity', 'logic', 'coverage', 'bounds'],\n}\npath = OUT / 'model_skeleton_results.json'\npath.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')\nprint(f'Wrote {path}')\n"""
    elif primary == 'prediction':
        model = common + """# Prediction skeleton: prevent leakage, create baseline, train/validate, report errors.\nresult = {'model_type': 'prediction', 'status': 'skeleton_not_trained', 'metrics': ['MAE', 'RMSE', 'MAPE/R2 as applicable']}\npath = OUT / 'model_skeleton_results.json'\npath.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')\nprint(f'Wrote {path}')\n"""
    elif primary == 'evaluation':
        model = common + """# Evaluation skeleton: normalize indicators, compute weights, rank alternatives, test stability.\nresult = {'model_type': 'evaluation', 'status': 'skeleton_not_ranked', 'checks': ['indicator_direction', 'weight_sum', 'rank_stability']}\npath = OUT / 'model_skeleton_results.json'\npath.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')\nprint(f'Wrote {path}')\n"""
    else:
        model = common + """# Generic modeling skeleton: replace with problem-specific executable model.\nresult = {'model_type': 'generic', 'status': 'skeleton_only'}\npath = OUT / 'model_skeleton_results.json'\npath.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')\nprint(f'Wrote {path}')\n"""
    return {'model_main_skeleton.py': model, 'check_constraints_skeleton.py': checker, 'sensitivity_skeleton.py': sensitivity}


def build_markdown(project: Path, routes: list[RouteResult], questions: list[str]) -> str:
    primary = routes[0].type_id
    lines = ["# 模型骨架路由报告\n\n", f"生成时间：{datetime.now().isoformat(timespec='seconds')}\n\n"]
    lines.append("## 题型识别\n\n")
    lines.append("| 排名 | 题型 | 分数 | 置信度 | 命中关键词 |\n|---:|---|---:|---|---|\n")
    for i, r in enumerate(routes, 1):
        lines.append(f"| {i} | {r.label} (`{r.type_id}`) | {r.score} | {r.confidence} | {', '.join(r.matched_keywords)} |\n")
    if questions:
        lines.append("\n## 小问清单\n\n")
        for q in questions:
            lines.append(f"- {q}\n")
    lines.append("\n## 推荐模型骨架\n\n")
    selected = [r.type_id for r in routes[:3] if r.type_id in TYPE_RULES]
    for tid in selected or [primary]:
        rule = TYPE_RULES.get(tid)
        if not rule:
            continue
        lines.append(f"### {rule['label']}\n\n")
        lines.append("**变量/参数：**\n")
        for x in rule['variables']:
            lines.append(f"- {x}\n")
        lines.append("\n**模型核心：**\n")
        for x in rule['model_core']:
            lines.append(f"- {x}\n")
        lines.append("\n**领域 checker 必须覆盖：**\n")
        for x in rule['checker']:
            lines.append(f"- {x}\n")
        lines.append("\n**验证/冲奖资产：**\n")
        for x in rule['validation']:
            lines.append(f"- {x}\n")
        lines.append("\n")
    lines.append("## 下一步执行要求\n\n")
    lines.append("1. 把 `02_代码/generated_skeleton/` 中的骨架改成题目特定模型；不得把 skeleton 结果当正式结果。\n")
    lines.append("2. 运行领域 checker，输出 `issue_count=0` 证据。\n")
    lines.append("3. 生成 baseline/主模型/敏感性或风险分析对比表。\n")
    lines.append("4. 再运行 `competition_evidence` 与 `competition_readiness` 门禁。\n")
    return ''.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('project')
    parser.add_argument('--write-code', action='store_true', help='write starter code under 02_代码/generated_skeleton')
    parser.add_argument('--strict', action='store_true', help='fail if type confidence is low/unknown')
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f'Project not found: {project}', file=sys.stderr)
        return 2
    analysis_path = project / '06_过程记录' / 'problem_analysis.md'
    text = read_text(analysis_path)
    if not text.strip():
        text = read_text(project / 'README.md')
    routes = route(text)
    questions = extract_questions(text)
    out_dir = project / '06_过程记录' / 'model_skeleton'
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'project': str(project),
        'source': str(analysis_path),
        'routes': [asdict(r) for r in routes],
        'primary_type': routes[0].type_id,
        'primary_confidence': routes[0].confidence,
        'questions': questions,
        'blocking_notes': [] if routes[0].type_id != 'unknown' else ['题型识别失败：请先补全 problem_analysis.md 的小问、目标、数据与输出要求。'],
    }
    (out_dir/'model_skeleton.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (out_dir/'model_skeleton.md').write_text(build_markdown(project, routes, questions), encoding='utf-8')
    if args.write_code:
        code_dir = project / '02_代码' / 'generated_skeleton'
        code_dir.mkdir(parents=True, exist_ok=True)
        for name, code in starter_code(routes[0].type_id).items():
            path = code_dir / name
            if not path.exists():
                path.write_text(code, encoding='utf-8')
    print(f"Model skeleton: {out_dir/'model_skeleton.md'}")
    print(f"Primary type: {routes[0].type_id} confidence={routes[0].confidence} score={routes[0].score}")
    if args.strict and (routes[0].type_id == 'unknown' or routes[0].confidence == 'low'):
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
