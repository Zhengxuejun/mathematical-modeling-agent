# 数学建模智能体 v1.3.0

- 当前源码发行版采用 Mozilla Public License 2.0。
- 恢复版权所有者名称为 `Zhengxuejun`。
- Pipeline 仅在本轮 finalizer 成功时报告 `completed`；被门禁阻断的重跑不再沿用历史 S8、旧包路径或旧 manifest 统计。
- Contest QC 新增 completed run 产物冻结：显式记录入口、输入、结果表和图表 SHA256，终稿前阻断未冻结、内容漂移或 run 输出关联不一致的 paper-ready 证据。
- Contest QC 对 paper-ready 结果、图表和主张实行非空唯一 ID 与类型化引用门禁，阻断空值、重复身份和 `result`/`figure` 类型错配形成的伪追溯。

- 支持项目脚手架、S0-S8、题型路由、领域 checker 模板、审计、提交包和竞赛就绪度。
- 增加竞赛质控账本：交付物锁定、真实数据 PoC、模型交接、数学核验、运行/结果/主张/图表追溯、P0/P1 与合规门禁。
- `competition_readiness_gate.py` 对明确失败、模板和未实现 checker 状态严格 fail-closed。
- 新建项目的包装脚本使用当前安装目录，不绑定某台机器的绝对路径。
- 完整 pipeline 先生成并审计最新报告，再通过最终质控和竞赛就绪度门禁，最后打包与更新 S8。
- 提交包改为 staging 自校验与原子替换，manifest v2.0 和 SHA256 共同阻止失败包、陈旧文件和路径逃逸。
- 人工编辑后的报告草稿默认不再被自动拼装器覆盖；开放 P1、模板内容或项目外证据会阻断正式交付。
- 通过 NOTICE 明确与 `usail-hkust/LLM-MM-Agent` 的方法论来源和代码/数据边界。
- Pull request 与 `main` 推送会在 Python 3.11、3.13 上自动运行完整测试，并配套贡献与安全报告规范。
- 新增 `contest_evidence_sync.py`：从题目解析、正式运行、结果表和图表生成待审核候选，幂等保留人工确认状态，并通过事务日志、回滚和恢复防止半写入。
- 完整 Pipeline 在报告审计后、Contest QC 前自动同步候选；schema、事务或重复身份冲突会阻断旧 QC 结果继续打包。
- 新增完全离线、确定性的 Modeling Benchmark Harness：使用三个原创合成案例和九个 fixture 检查优化可行性、分组预测泄漏、评价排序稳定性、复现记录与证据一致性。
- Benchmark 提供 `run`、`validate`、`suite` 三个命令，输出稳定 JSON/Markdown；它不调用 LLM，不使用网络，也不会自动改变 `competition_ready`。
- 新增 `candidate_solution_tree.py`：以有限节点/深度记录 baseline 和父子改进分支，验证输入与证据哈希、运行、可行性和验证结果，并支持同 case Benchmark 下的确定性选优。
- 候选树不执行记录命令；不同输入快照或不同 Benchmark case 拒绝比较，`selected` 不会写入 Contest QC、S0-S8、提交包或 `competition_ready`。
- README 新增端到端比赛工作流图和状态边界表，并增加 `docs/competition-workflow.md`，集中说明候选开发、Pipeline 真实顺序、门禁、修复回路和 72 小时比赛节奏。
