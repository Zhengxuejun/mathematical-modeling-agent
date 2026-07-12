# 竞赛质控门禁（Contest QC Gate）

`contest_qc_gate.py` 是 `mathematical-modeling-agent` 的竞赛级证据层。它吸收“题目锁定—交付物—真实数据 PoC—模型交接—数学核验—可复现运行—主张/图表证据—评委风险—提交合规”的核心思想，但保持一个可执行的 umbrella skill，不拆成多个常驻子技能。

## 何时使用

- 新竞赛项目建立后：初始化登记表与质控材料。
- 主模型、真实附件 PoC 和正式运行完成后：运行 `--phase model`，确认结果可以进入论文证据层，且代码没有自行猜单位、约束、输出字段或阈值。
- 报告、PDF、提交包前：运行 `--phase final`；它只检查证据与合规边界，不承诺获奖。

不要为局部措辞、普通图表修复或探索性代码强制开启完整门禁。那类结果保持 `diagnostic-only`，直到要被提升为论文/提交结论。

## 命令

在项目根目录：

```bash
# 仅创建模板；不覆盖已有登记表内容
python 02_代码/17_contest_qc.py --init --phase early

# 题目锁定和交付物检查
python 02_代码/17_contest_qc.py --phase early --strict

# 主模型进入正式求解前的证据门禁
python 02_代码/17_contest_qc.py --phase model --strict

# 终稿前证据、评委风险、匿名与复现门禁
python 02_代码/17_contest_qc.py --phase final --strict
```

输出：

```text
06_过程记录/竞赛质控/contest_qc_gate.json
06_过程记录/竞赛质控/contest_qc_gate.md
```

## 三阶段口径

| Phase | 目的 | 必须成立 |
|---|---|---|
| `early` | 题目进入建模前 | 实质性 `problem_analysis.md`；每问/每个输出有 `deliverable_matrix.csv` 行；无 blocked 交付物 |
| `model` | 主模型完成后、进入报告证据层前 | 所有交付物完成或正式豁免；模型交接完整；真实附件 PoC 通过；数学检查无硬失败；存在可复现 run 和结果登记 |
| `final` | 终稿与提交包前 | `model` 全部通过；论文主张映射到 `paper_ready` 结果/图；无开放 P0/P1；至少五项可定位通过检查；当前官方规则、匿名、复现和 AI 披露状态明确 |

状态只表示门禁证据：

```text
blocked       存在缺失或矛盾的硬证据，不能提升为正式结论
needs_review  没有硬阻塞，但审查材料还不完整
early_ready   早期题目锁定通过
model_ready   模型级证据通过
final_ready   当前提交级证据通过；不代表必然获奖
```

## 核心登记表

所有文件在 `06_过程记录/竞赛质控/` 下；`--init` 只建空表头和模板，不会伪造任何通过状态。

- `deliverable_matrix.csv`：每个小问的精确输出，防止答非所问；`accepted_omission` 必须填写 `approval_source`、`omission_reason` 和 `accepted_by`，不能作为方便跳题的状态。
- `model_handoff.md`：模型到代码的交接契约。代码不得自行猜测变量单位、目标、约束、参数、阈值或结果 schema。
- `poc_registry.csv`：主路线/基线必须有可追溯到真实附件的 passed PoC。synthetic/mock 只能是 diagnostic-only。
- `math_verification.csv`：量纲、边界、守恒、约束、公式回代、可行性措辞等硬检查。
- `run_record.csv` 与 `result_registry.csv`：把数值与可复现命令、输入、参数、seed、源表绑定；`result_registry.csv.deliverable_id` 必须映射到题目交付物。
- `claim_ledger.csv` 与 `figure_evidence.csv`：摘要/结论/主图必须映射到 `paper_ready` 证据；主图还要有 run、caption、图后结论以及 render 或人工可读性检查，`figure_evidence.csv.deliverable_id` 使每个交付物可追溯。
- `review_findings.csv`：P0/P1/P2/P3 评委风险。终稿前不允许开放 P0/P1。
- `review_pass_items.csv`：终稿至少五项可定位的通过证据，避免只写“已检查”。
- `submission_checklist.md`：来自当前官方规则的格式、匿名、复现和 AI 披露状态；禁止沿用往年规则猜测。

## 与现有 Pipeline 的关系

总控 Pipeline 在报告拼装后自动运行 `contest_qc_gate.py --phase final`，并在随后的 `competition_evidence_builder.py` 与 `competition_readiness_gate.py` 中读取其输出。

- `contest_qc_gate`：证据账本、评委风险、提交合规的细粒度门禁。
- `competition_evidence_builder`：从项目文件生成证据索引，识别 placeholder、模板 checker 和模型信号。
- `competition_readiness_gate`：把 workflow/model/competition 分层，给出是否达到可参赛评审口径的综合判断。

三者互补：`final_ready` 不是 `competition_ready` 的替代；后者仍会因 placeholder、未实现领域 checker、模型结果不足等原因拦截项目。

## 红线

- 不把模板、生成骨架、演示数据、单次试跑或好看的图提升为 `paper_ready`。
- 不把模型名字、没有真实数据 PoC 的方法或没有单位/约束的公式交给正式代码。
- 不让摘要/结论引用未冻结的数值、未验证图表或未完成 run。
- 不因“自动检查全绿”声称必然获奖；真实题意、模型合理性和论文洞见仍需人工/智能体审查。
