# 安装说明：数学建模智能体 v1.2.0

## 安装到 Hermes

1. 解压本压缩包。
2. 将 `mathematical-modeling-agent/` 整个目录复制到：

```text
~/.hermes/skills/data-science/mathematical-modeling-agent/
```

3. 新开 Hermes 会话后加载：

```text
/skill mathematical-modeling-agent
```

## 新建竞赛项目

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/create_modeling_project.py "2026国赛项目" --base ~/Documents/数学建模
cd ~/Documents/数学建模/2026国赛项目
python 02_代码/17_contest_qc.py --phase early
```

## 重要边界

- `final_ready` 与 `competition_ready` 是证据与就绪度状态，不承诺获奖。
- 终稿前应填充真实附件 PoC、可复现 run、结果/图表/主张映射以及当前规则、匿名和 AI 披露要求。
- 本包排除测试缓存、字节码和本机绝对路径；项目包装脚本会自动绑定安装后的 skill 路径。
- 本仓库内容使用 MIT License；上游研究项目材料不适用本仓库授权，详见 `NOTICE`。
