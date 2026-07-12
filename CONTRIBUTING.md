# Contributing

感谢改进 Mathematical Modeling Agent。默认协作方式是 feature branch 或 fork 加 pull request，不直接向 `main` 推送未经验证的修改。

## 开发流程

1. 从最新 `main` 创建范围明确的分支。
2. 保持现有 CLI、项目目录和 JSON/CSV 契约兼容；有意破坏兼容时必须在 pull request 中明确说明。
3. 为行为变化或缺陷修复增加回归测试。
4. 在本地运行：

   ```bash
   python3 -m compileall -q scripts
   python3 -m pytest -q
   ```

5. 仓库文件发生变化时重新生成 `PACKAGE_MANIFEST.json`，保证路径、字节数和 SHA256 与提交内容一致。
6. 提交 pull request，说明问题、修改、验证证据和兼容性影响。
7. 等待 GitHub 上的 Python 3.11 与 Python 3.13 检查通过后再合并。

## 变更边界

- 优先增强可复现性、证据追溯、门禁可靠性和真实比赛工作流。
- 历史题应作为测试 fixture，不应把通用智能体硬编码成某一道题的专项解法。
- 不提交竞赛私有附件、未公开题目或解答、个人路径、凭据、缓存、模型权重和大型生成文件。
- 不复制许可证与本仓库不兼容的上游源码、数据、提示词或媒体。来源与许可边界必须在 pull request 和 `NOTICE` 中说明。
- 不把 S8、`final_ready` 或 `competition_ready` 描述为数学正确性或获奖保证。

## Commit 与 Pull Request

Commit 应使用清晰的命令式摘要。Pull request 应保持单一目的，避免混入无关格式化或大范围重构。评审重点依次是行为正确性、证据完整性、回归风险和测试覆盖。

