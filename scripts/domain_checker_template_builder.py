#!/usr/bin/env python3
"""Generate domain checker templates from model_skeleton routing results.

This component turns early problem-type routing into executable checker stubs.
Generated checks contain TODO/warn items until project-specific variables and
result schemas are wired in. A project is not `model_ready` merely because these
templates exist.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

CHECKER_LIBRARY = {
    "optimization": {
        "label": "优化/资源配置 checker",
        "checks": [
            {"id": "capacity_bounds", "desc": "资源/容量/面积/预算不超过上限", "severity": "fail"},
            {"id": "coverage_or_assignment", "desc": "所有必选对象被覆盖，唯一性/分配逻辑满足", "severity": "fail"},
            {"id": "variable_bounds", "desc": "决策变量满足非负、整数、0-1 或上下界要求", "severity": "fail"},
            {"id": "objective_recompute", "desc": "目标函数能从结果表和参数复算", "severity": "fail"},
            {"id": "solver_status", "desc": "求解器状态、gap、可行性日志可审计", "severity": "warn"},
        ],
    },
    "network_routing": {
        "label": "路径/网络/物流 checker",
        "checks": [
            {"id": "node_visit", "desc": "每个需求点访问次数满足题目要求", "severity": "fail"},
            {"id": "route_connectivity", "desc": "路径连续、无断链、起终点合法", "severity": "fail"},
            {"id": "vehicle_capacity", "desc": "车辆载重/容量/配送量不超限", "severity": "fail"},
            {"id": "time_window", "desc": "到达时间、服务时间、时间窗满足约束", "severity": "fail"},
            {"id": "distance_cost_recompute", "desc": "总距离/成本可由路径明细复算", "severity": "fail"},
            {"id": "route_visualization", "desc": "关键路径有图示或节点-边明细", "severity": "warn"},
        ],
    },
    "prediction": {
        "label": "预测/回归 checker",
        "checks": [
            {"id": "train_test_split", "desc": "训练/验证/测试划分符合时间或主体隔离要求", "severity": "fail"},
            {"id": "leakage_guard", "desc": "特征不含未来信息、目标泄漏或重复观测泄漏", "severity": "fail"},
            {"id": "baseline_metric", "desc": "至少有 naive/均值/移动平均/线性模型 baseline", "severity": "fail"},
            {"id": "error_metrics", "desc": "误差指标 MAE/RMSE/MAPE/R2/分类指标按任务输出", "severity": "fail"},
            {"id": "residual_diagnosis", "desc": "残差、异常值或误差分布有诊断", "severity": "warn"},
        ],
    },
    "evaluation": {
        "label": "综合评价 checker",
        "checks": [
            {"id": "indicator_direction", "desc": "正向/逆向/区间型指标方向处理正确", "severity": "fail"},
            {"id": "normalization_range", "desc": "标准化结果范围合理且无除零/全常数问题", "severity": "fail"},
            {"id": "weight_sum", "desc": "权重非负且和为 1", "severity": "fail"},
            {"id": "ranking_recompute", "desc": "综合得分和排序可由标准化矩阵与权重复算", "severity": "fail"},
            {"id": "rank_stability", "desc": "权重扰动/替代方法下排序稳定性有记录", "severity": "warn"},
        ],
    },
    "simulation": {
        "label": "仿真/随机情景 checker",
        "checks": [
            {"id": "random_seed", "desc": "随机种子固定且可复现", "severity": "fail"},
            {"id": "distribution_parameters", "desc": "随机变量分布和参数来源明确", "severity": "fail"},
            {"id": "scenario_count", "desc": "仿真次数/情景数量足够，并做收敛性说明", "severity": "warn"},
            {"id": "risk_metrics", "desc": "均值、标准差、分位数、CVaR/最坏情景等风险指标输出", "severity": "fail"},
            {"id": "stress_feasibility", "desc": "极端情景下不违反硬约束，或明确失败概率", "severity": "fail"},
        ],
    },
    "statistics": {
        "label": "统计检验 checker",
        "checks": [
            {"id": "independence", "desc": "样本独立性/重复测量/聚类结构已处理", "severity": "fail"},
            {"id": "test_assumptions", "desc": "正态性、方差齐性、线性等检验前提有诊断", "severity": "warn"},
            {"id": "multiple_testing", "desc": "多重检验时有校正或解释", "severity": "warn"},
            {"id": "effect_size_ci", "desc": "报告效应量和置信区间，不只报告 p 值", "severity": "fail"},
            {"id": "robust_model", "desc": "替代模型/稳健标准误/分层分析验证结论", "severity": "warn"},
        ],
    },
    "unknown": {
        "label": "通用 checker",
        "checks": [
            {"id": "problem_specific_schema", "desc": "补充题目特定结果 schema 和硬约束", "severity": "fail"},
            {"id": "result_non_empty", "desc": "核心结果表非空且字段可解释", "severity": "fail"},
            {"id": "answer_each_question", "desc": "每个小问都有直接答案和证据", "severity": "fail"},
        ],
    },
}

CHECKER_CODE_TEMPLATE = '''from pathlib import Path
import csv
import json

BASE = Path(__file__).resolve().parents[1]
TABLE_DIR = BASE / '03_结果表格'
OUT_DIR = BASE / '06_过程记录' / '领域checker'
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHECK_SPEC = __CHECK_SPEC__


def read_csv_rows(path: Path):
    try:
        with path.open('r', encoding='utf-8-sig', errors='ignore', newline='') as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def table_has_rows(name_contains: str = '') -> bool:
    for path in TABLE_DIR.glob('*.csv'):
        if name_contains and name_contains.lower() not in path.name.lower():
            continue
        rows = read_csv_rows(path)
        if rows and any(any(str(v).strip() for v in r.values()) for r in rows):
            return True
    return False


def add(results, check_id, status, message, evidence=''):
    results.append({'id': check_id, 'status': status, 'message': message, 'evidence': evidence})


def run_checks():
    results = []
    add(results, 'core_result_table_exists', 'pass' if table_has_rows() else 'fail', '至少一个 CSV 结果表非空', str(TABLE_DIR))
    for spec in CHECK_SPEC['checks']:
        add(results, spec['id'], 'warn', 'TODO: ' + spec['desc'], 'template requires project-specific implementation')
    return results


def main():
    checks = run_checks()
    issue_count = sum(1 for c in checks if c['status'] == 'fail')
    warn_count = sum(1 for c in checks if c['status'] == 'warn')
    payload = {
        'checker_type': CHECK_SPEC['type_id'],
        'checker_label': CHECK_SPEC['label'],
        'issue_count': issue_count,
        'warn_count': warn_count,
        'checks': checks,
    }
    out_json = OUT_DIR / f"domain_checker_{CHECK_SPEC['type_id']}.json"
    out_md = OUT_DIR / f"domain_checker_{CHECK_SPEC['type_id']}.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [f"# {CHECK_SPEC['label']}\n\n", f"issue_count={issue_count}, warn_count={warn_count}\n\n", '| id | status | message | evidence |\n|---|---|---|---|\n']
    for c in checks:
        lines.append(f"| {c['id']} | {c['status']} | {c['message']} | {c.get('evidence','')} |\n")
    out_md.write_text(''.join(lines), encoding='utf-8')
    print(f'Wrote {out_json}; issue_count={issue_count}; warn_count={warn_count}')
    return 1 if issue_count else 0

if __name__ == '__main__':
    raise SystemExit(main())
'''


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def selected_types(project: Path, max_types: int) -> list[str]:
    skeleton = read_json(project / '06_过程记录' / 'model_skeleton' / 'model_skeleton.json')
    routes = skeleton.get('routes') or []
    types = []
    for r in routes:
        tid = r.get('type_id')
        if tid in CHECKER_LIBRARY and tid not in types:
            types.append(tid)
    if not types:
        primary = skeleton.get('primary_type') or 'unknown'
        types = [primary if primary in CHECKER_LIBRARY else 'unknown']
    return types[:max_types]


def write_checker(project: Path, type_id: str, force: bool) -> Path:
    code_dir = project / '02_代码' / 'generated_checkers'
    code_dir.mkdir(parents=True, exist_ok=True)
    spec = dict(CHECKER_LIBRARY[type_id])
    spec['type_id'] = type_id
    path = code_dir / f'check_{type_id}.py'
    code = CHECKER_CODE_TEMPLATE.replace('__CHECK_SPEC__', repr(spec))
    if force or not path.exists():
        path.write_text(code, encoding='utf-8')
    return path


def write_index(project: Path, types: list[str], paths: list[Path]) -> tuple[Path, Path]:
    out_dir = project / '06_过程记录' / '领域checker'
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'project': str(project),
        'checker_types': types,
        'checker_files': [str(p.relative_to(project)) for p in paths],
        'note': 'Generated templates are not formal checker evidence until TODO checks are replaced with project-specific executable checks.',
    }
    json_path = out_dir / 'domain_checker_templates.json'
    md_path = out_dir / 'domain_checker_templates.md'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# 领域 checker 模板索引\n\n', f"生成时间：{payload['generated_at']}\n\n", '| 题型 | checker 文件 | 必须落地的检查 |\n|---|---|---|\n']
    for tid, p in zip(types, paths):
        checks = '；'.join(c['desc'] for c in CHECKER_LIBRARY[tid]['checks'])
        lines.append(f"| {CHECKER_LIBRARY[tid]['label']} (`{tid}`) | `{p.relative_to(project)}` | {checks} |\n")
    lines.append('\n> 注意：模板中的 TODO/warn 必须替换为读取正式结果表的硬检查；否则不能作为 `model_ready` 证据。\n')
    md_path.write_text(''.join(lines), encoding='utf-8')
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('project')
    parser.add_argument('--max-types', type=int, default=3)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--strict', action='store_true', help='fail if no model_skeleton routing exists')
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f'Project not found: {project}', file=sys.stderr)
        return 2
    skeleton_path = project / '06_过程记录' / 'model_skeleton' / 'model_skeleton.json'
    if args.strict and not skeleton_path.exists():
        print(f'Missing model skeleton: {skeleton_path}', file=sys.stderr)
        return 1
    types = selected_types(project, args.max_types)
    paths = [write_checker(project, tid, args.force) for tid in types]
    json_path, md_path = write_index(project, types, paths)
    print(f'Domain checker templates: {md_path}')
    print('Types:', ', '.join(types))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
