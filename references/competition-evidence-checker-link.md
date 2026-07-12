# 竞赛证据汇总器与领域 checker 联动

## 目标

本补丁增强 `competition_evidence_builder.py` 对领域 checker 的识别能力，防止把“生成了 checker 模板”误判为“正式约束检查通过”。

## 新增判定层级

`domain_checker.implementation.status` 现在区分：

```text
not_detected
checker_detected_no_machine_output
template_checker_only
implemented_checker_warn
implemented_checker_fail
implemented_checker_pass
```

其中只有：

```text
implemented_checker_pass
```

才会让 `domain_checker.status=pass`。

## 判定口径

### template_checker_only

检测到：

```text
06_过程记录/领域checker/domain_checker_templates.json/md
02_代码/generated_checkers/check_*.py
02_代码/generated_skeleton/check_constraints_skeleton.py
```

但没有正式 checker 输出。此状态不能算 `model_ready`。

### implemented_checker_warn

存在 checker 输出，且 `issue_count=0`，但仍存在：

- `warn_count>0`；
- TODO/template/starter 痕迹；
- 未替换模板检查项。

此状态说明 checker 有进展，但仍不能直接宣称冲奖级就绪。

### implemented_checker_fail

正式 checker 输出 `issue_count>0`。必须先修硬约束。

### implemented_checker_pass

要求：

```text
正式 checker 输出存在
issue_count=0
warn_count=0
无 TODO/template/starter 残留
```

只有该状态可作为 `competition_evidence.domain_checker.status=pass`。

## 输出字段

`competition_evidence.json` 中新增：

```json
"domain_checker": {
  "status": "template_checker_only | implemented_checker_warn | implemented_checker_fail | pass | ...",
  "implementation": {
    "status": "...",
    "template_index_detected": true,
    "generated_checker_files": [],
    "implemented_checker_files": [],
    "outputs": [],
    "issue_count": null,
    "warn_count": 0,
    "todo_hits": 0
  }
}
```

## 重要原则

生成 checker 模板是建模生产系统的一部分，但不是竞赛证据本身。正式比赛中，必须把模板变成针对该题数据结构和结果表的硬检查，再由证据汇总器读取其输出。
