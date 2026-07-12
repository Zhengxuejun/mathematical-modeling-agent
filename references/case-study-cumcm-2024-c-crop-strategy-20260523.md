# Case Study: CUMCM 2024 C Crop Planting Strategy Solver Upgrade

## Session trigger

User asked to continue testing the mathematical-modeling-agent on real CUMCM problems with the explicit target: “能真正打比赛，并且能获奖”. This moved the task from lightweight S0-S8 workflow validation to competition-grade modeling capability.

## Official problem used

- Competition: 2024 高教社杯全国大学生数学建模竞赛
- Problem: C 题《农作物的种植策略》
- Source: official CUMCM website `mcm.edu.cn`, `CUMCM2024Problems.zip`
- Key inputs: `C题.pdf`, `附件1.xlsx`, `附件2.xlsx`, `result1_1.xlsx`, `result1_2.xlsx`, `result2.xlsx`

## Durable lessons

### 1. Pipeline completion is not competition readiness

A project can reach S8 with a placeholder baseline and still be mathematically inadequate. For real competition use, the agent must distinguish:

- **workflow completed**: files exist, quality scripts pass, report draft/submit package generated;
- **model completed**: decision variables, constraints, objective, result files and validation match the problem;
- **award-ready**: solution is feasible, defensible, compared against baselines, risk-tested, and written persuasively.

Do not tell the user a real contest problem is “done” merely because `recommended_status=completed`.

### 2. Excel-first data handling is mandatory for CUMCM

CUMCM attachments are often `.xlsx` with multiple sheets, notes rows, merged-like formatting, and official result templates. Default baseline scripts that only scan CSV will produce empty summaries and create a false sense of success.

Required behavior for CUMCM-style tasks:

- read all sheets in Excel attachments;
- coerce ID columns with `pd.to_numeric(..., errors='coerce')` and drop note rows such as `注：`;
- parse price ranges like `2.50-4.00` as midpoint or explicit interval;
- preserve raw files under `01_原始数据/` and write filled templates to `03_结果表格/`;
- never treat empty numeric summaries as sufficient for a data-rich Excel problem.

### 3. Official result-template filling is a first-class deliverable

For CUMCM 2024 C, the real deliverables are not just CSV summaries; the solver must fill:

- `result1_1.xlsx` for Q1 waste scenario;
- `result1_2.xlsx` for Q1 discount scenario;
- `result2.xlsx` for Q2 uncertainty scenario.

The template writer must preserve workbook/sheet structure and write planting areas into year sheets by land row, season block, and crop column. A solution that only emits `model_results.csv` is not contest-ready.

### 4. Constraint checker must be domain-specific

For crop planting optimization, generic quality gates are insufficient. Add a dedicated checker for at least:

1. per-land per-season total planted area ≤ land area;
2. crop-land-season suitability;
3. three-year bean/legume coverage windows, including 2023 as initial history;
4. filled template non-emptiness and row/column alignment;
5. later upgrade: complete no-consecutive-replanting across years/seasons, minimum area thresholds, crop dispersion/concentration.

The checker output should include `issue_count`; competition-stage summaries should report this value explicitly.

### 5. Feasible heuristic before full MIP, but label it honestly

A fast heuristic that creates feasible plans and passes the domain checker is valuable as the first competition MVP. However, label it as “可行启发式原型” unless a real MIP/LP/DP/global optimization is implemented and solved.

For award-readiness, next stage should upgrade to rolling MIP or grouped MIP:

- decision variable `x[y,s,l,c]` for planted area;
- optional binary `z[y,s,l,c]` for whether a crop is used;
- normal sales and surplus variables;
- objective: revenue minus cost minus dispersion/small-area/risk penalties;
- constraints: area, suitability, rotation/no replanting, bean coverage, demand/surplus, template feasibility.

### 6. Problem 2/3 require risk evidence, not just altered parameters

For uncertainty/correlation questions, a persuasive contest solution needs simulation evidence:

- Monte Carlo scenarios for demand, yield, cost, price;
- mean profit, standard deviation, 5% quantile, CVaR or downside risk;
- comparison of Q2 robust plan vs Q3 correlated/substitution-aware plan;
- clear assumptions for substitutability/complementarity matrix and price-demand/cost correlations.

### 7. Award-ready report requirements

After generating feasible templates, immediately convert technical outputs into paper-ready assets:

- real summary values in abstract;
- formula-numbered objective and constraints;
- algorithm flowchart/pseudocode;
- result tables for each question;
- figures: profit comparison, crop area structure, land-type utilization, risk distribution, bean rotation coverage;
- limitations: heuristic vs exact optimum, assumptions behind demand estimation and correlations.

## Implementation pattern from session

A useful project-specific solver script pattern:

```text
02_代码/13_cumcm2024c_solver.py
  load_data()                # read Excel sheets, clean note rows
  prepare_parameters()       # crop/land/stat maps and 2023-derived demand
  land_allowed()             # crop-land-season rule engine
  make_multi_year_plan()     # heuristic or MIP plan generation
  evaluate_plan()            # revenue/cost/profit by crop/year/season
  write_template()           # preserve official xlsx template structure
  check_plan()               # domain-specific feasibility checker
  make_figures()             # paper figures
```

## Skill update recommendation

When future user says “真正打比赛/能获奖/国赛题测试”, default to competition-grade mode:

1. complete official material acquisition and audit;
2. build a domain-specific solver or model, not only generic baseline;
3. write official result templates when required;
4. run a domain-specific checker;
5. generate paper-ready results and explicitly distinguish MVP/heuristic/exact/award-ready levels.
