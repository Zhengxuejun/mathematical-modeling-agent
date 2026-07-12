# Excel 多表数据审计模板

用于数学建模竞赛附件的快速审计，尤其适合中文列名、多 sheet、重复主体、比例/质量控制字段。

```python
from pathlib import Path
import pandas as pd
import json
import re

INPUT = Path('data/raw/附件.xlsx')
OUT = Path('results/tables')
OUT.mkdir(parents=True, exist_ok=True)


def parse_week(x):
    """把 11w+6、11周6天、11+6 等孕周格式转为浮点周。无法解析返回 None。"""
    if pd.isna(x):
        return None
    s = str(x).strip().lower()
    m = re.match(r'^(\d+)\s*w\s*\+?\s*(\d+)?$', s)
    if m:
        return int(m.group(1)) + int(m.group(2) or 0) / 7
    m = re.match(r'^(\d+)\s*周\s*(\d+)?\s*天?$', s)
    if m:
        return int(m.group(1)) + int(m.group(2) or 0) / 7
    m = re.match(r'^(\d+)\s*\+\s*(\d+)$', s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 7
    try:
        return float(s)
    except ValueError:
        return None


def audit_excel(path: Path):
    xl = pd.ExcelFile(path)
    workbook_report = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet)
        df.columns = [str(c).strip() for c in df.columns]

        col_report = []
        for c in df.columns:
            ser = df[c]
            item = {
                'column': c,
                'dtype': str(ser.dtype),
                'missing': int(ser.isna().sum()),
                'missing_rate': float(ser.isna().mean()),
                'nunique': int(ser.nunique(dropna=True)),
            }
            if pd.api.types.is_numeric_dtype(ser):
                item.update({
                    'min': None if ser.dropna().empty else float(ser.min()),
                    'max': None if ser.dropna().empty else float(ser.max()),
                    'mean': None if ser.dropna().empty else float(ser.mean()),
                })
            col_report.append(item)

        sheet_report = {
            'sheet': sheet,
            'rows': int(len(df)),
            'cols': int(len(df.columns)),
            'columns': list(df.columns),
            'columns_report': col_report,
        }

        # 常见主体 ID 重复检查
        for id_col in ['孕妇代码', '患者ID', '样本编号', '运动者编号', '设备编号']:
            if id_col in df.columns:
                counts = df.groupby(id_col).size()
                sheet_report[f'{id_col}_unique'] = int(counts.size)
                sheet_report[f'{id_col}_repeated_subjects'] = int((counts > 1).sum())
                break

        # 常见比例字段范围检查
        ratio_cols = [c for c in df.columns if any(k in c for k in ['比例', '浓度', 'GC含量', '率'])]
        range_issues = {}
        for c in ratio_cols:
            if pd.api.types.is_numeric_dtype(df[c]):
                bad = df[(df[c] < -1e-9) | (df[c] > 1 + 1e-9)]
                if len(bad):
                    range_issues[c] = int(len(bad))
        sheet_report['ratio_range_issues_0_1'] = range_issues

        # GC 质量控制：题目若给 40%-60% 正常范围
        for c in [c for c in df.columns if 'GC含量' in c]:
            if pd.api.types.is_numeric_dtype(df[c]):
                sheet_report[f'{c}_outside_40_60_pct'] = int(((df[c] < 0.4) | (df[c] > 0.6)).sum())

        # 孕周解析
        for c in [c for c in df.columns if '孕周' in c]:
            parsed = df[c].map(parse_week)
            sheet_report[f'{c}_parsed_missing'] = int(pd.isna(parsed).sum())
            if pd.Series(parsed).notna().any():
                sheet_report[f'{c}_parsed_min'] = float(pd.Series(parsed).min())
                sheet_report[f'{c}_parsed_max'] = float(pd.Series(parsed).max())

        workbook_report.append(sheet_report)

    return workbook_report


if __name__ == '__main__':
    report = audit_excel(INPUT)
    (OUT / 'data_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    # 扁平化字段审计表，便于粘到报告
    rows = []
    for sh in report:
        for c in sh['columns_report']:
            rows.append({'sheet': sh['sheet'], **c})
    pd.DataFrame(rows).to_csv(OUT / 'data_audit_columns.csv', index=False, encoding='utf-8-sig')
    print(json.dumps([{k: v for k, v in sh.items() if k != 'columns_report'} for sh in report], ensure_ascii=False, indent=2))
```
