# CDISC / SDTM / ADaM / TFL 小白学习手册（真实数据版）

> 适用人群：统计编程 / 生物统计 / 数据管理方向的入门者、转行者、应届生。
> 学完你应该能：说清楚一份临床试验数据从 CRF 到 CSR 表格的完整链路；看懂 SDTM 和 ADaM 数据集；自己算出一张人口学表、一张 AE 表、一张 KM 图，并知道怎么 QC。
>
> **所有例子都来自 GitHub 上的公开真实数据**（CDISC 官方 Pilot 研究 CDISCPILOT01，一项阿尔茨海默病 Xanomeline 透皮贴剂 vs 安慰剂的 26 周随机双盲试验）：
>
> - SDTM：[`pharmaverse/pharmaversesdtm`](https://github.com/pharmaverse/pharmaversesdtm)（固定 commit `7ec53ea`）
> - ADaM：[`cdisc-org/sdtm-adam-pilot-project`](https://github.com/cdisc-org/sdtm-adam-pilot-project)（固定 commit `667511d`，Dataset-JSON 格式）
>
> 手册里出现的每一个数字都可以用 `python scripts/build_cdisc_learning_examples.py` 复现，结果在 [`generated/real_data_examples.md`](generated/real_data_examples.md)。
>
> 配套面试版：[`02_interview_guide.md`](02_interview_guide.md)

---

## 目录

0. [一张图看懂整条链路](#0-一张图看懂整条链路)
1. [CDISC 是什么？为什么必须学？](#1-cdisc-是什么为什么必须学)
2. [SDTM：把“收集到的数据”标准化](#2-sdtm把收集到的数据标准化)
3. [ADaM：把数据变成“一步就能分析”](#3-adam把数据变成一步就能分析)
4. [TFL：最终交付给统计师、医学和监管的表/列表/图](#4-tfl最终交付给统计师医学和监管的表列表图)
5. [实战：一个受试者从 SDTM 走到 TFL](#5-实战一个受试者从-sdtm-走到-tfl)
6. [QC：为什么要双人独立编程（真实差异案例）](#6-qc为什么要双人独立编程真实差异案例)
7. [代码示意：SAS / R(admiral) / Python](#7-代码示意sas--radmiral--python)
8. [新手最常踩的 12 个坑](#8-新手最常踩的-12-个坑)
9. [术语表](#9-术语表)
10. [练习题（附答案）](#10-练习题附答案)
11. [学习路线与资源](#11-学习路线与资源)

---

## 0. 一张图看懂整条链路

```text
 Protocol（方案） + SAP（统计分析计划） + TFL Shells（表格模板）
        │                         │
        ▼                         │ 告诉你“要算什么”
 CRF / EDC 采集（CDASH 标准）       │
        │                         │
        ▼  映射 (mapping)          │
 ┌──────────────┐                 │
 │   SDTM       │  “如实记录发生了什么”：DM, AE, EX, DS, LB, VS, QS ...
 └──────┬───────┘                 │
        ▼  推导 (derivation)       │
 ┌──────────────┐                 │
 │   ADaM       │  “为分析而准备”：ADSL, ADAE, ADQSxxx, ADTTE ...
 └──────┬───────┘                 │
        ▼  汇总 / 建模             ▼
 ┌──────────────────────────────────────┐
 │  TFL：Tables / Listings / Figures     │ ──► CSR（临床研究报告）
 └──────────────────────────────────────┘
        +  Define-XML（元数据说明书）、ADRG/SDRG（审阅指南）
        +  Pinnacle 21 / CDISC CORE 合规检查
        ──► eCTD Module 5 递交给 FDA / PMDA / NMPA
```

一句话记忆：**SDTM 记录事实，ADaM 服务分析，TFL 呈现结论。**

| 层 | 回答的问题 | 典型使用者 | 真实例子（CDISCPILOT01） |
|---|---|---|---|
| SDTM | 发生了什么？ | 数据管理、SDTM 程序员、审评员 | DM 306 人（含 52 名筛选失败） |
| ADaM | 分析需要什么？ | 统计程序员、统计师 | ADSL 254 名随机化受试者 |
| TFL | 结论是什么？ | 统计师、医学、监管 | 第 24 周 ADAS-Cog 剂量反应 p=0.245 |

---

## 1. CDISC 是什么？为什么必须学？

**CDISC**（Clinical Data Interchange Standards Consortium，临床数据交换标准协会）是一个非营利组织，制定临床研究数据的“通用语言”。你可以把它理解为“临床试验数据的国标”。

为什么必须学：

- **FDA**：2016 年 12 月 17 日之后开始的研究，NDA/BLA 等递交原则上需要按 FDA Data Standards Catalog 使用 CDISC 标准（SDTM、ADaM、Define-XML）。
- **PMDA（日本）**：同样要求以 CDISC 格式递交电子数据。
- **NMPA（中国）**：《药物临床试验数据递交指导原则》（2020）鼓励采用 CDISC 标准递交。
- **行业现实**：几乎所有药企/CRO 的统计编程岗位 JD 都写着 “SDTM / ADaM / TLF”。

CDISC 家族里你最需要知道的成员：

| 标准 | 用途 | 小白一句话 |
|---|---|---|
| CDASH | 数据采集（CRF 设计） | 源头怎么收 |
| SDTM / SDTMIG | 制表数据模型 | 收上来怎么整理 |
| SEND | 非临床（动物）版 SDTM | 毒理研究用 |
| ADaM / ADaMIG | 分析数据模型 | 怎么为分析做准备 |
| Controlled Terminology (CT) | 受控术语 | 规定“SEX 只能填 M/F/U/UNDIFFERENTIATED” |
| Define-XML | 元数据 | 数据集的“说明书” |
| Dataset-JSON | 新一代交换格式 | 未来替代 SAS XPT v5 |
| ARS（Analysis Results Standard） | 分析结果元数据 | 把 TFL 也标准化 |

> 本仓库的 Pilot ADaM 就是 **Dataset-JSON** 格式（见 `cache/learning/adsl.json`），而递交给 FDA 的仍以 **SAS XPT v5** 为主（本仓库 v0.28 有 XPT 投影示例）。

---

## 2. SDTM：把“收集到的数据”标准化

### 2.1 核心思想

- **按“域（Domain）”组织**：每个域是一个数据集，名字两个字母，例如 DM、AE。
- **尽量不做推导**：SDTM 忠实反映收集的数据（只允许少量标准推导，如 `--DY` 研究日、`AGE`）。
- **一切都可追溯到 CRF**。

### 2.2 域的四大类（必背）

| 类别 | 含义 | 常见域 |
|---|---|---|
| Special-Purpose | 特殊用途 | **DM** 人口学、CO 评论、SE/SV 访视 |
| Interventions | 给受试者“做了什么” | **EX** 给药、CM 合并用药、PR 操作 |
| Events | 受试者“发生了什么” | **AE** 不良事件、**DS** 处置、MH 病史 |
| Findings | “测出了什么” | **LB** 实验室、**VS** 生命体征、**QS** 问卷、EG 心电图 |

另外还有 Trial Design 域（TA、TE、TV、TI、TS），描述试验设计本身。

### 2.3 关键变量（所有域通用）

| 变量 | 含义 | 例子（真实） |
|---|---|---|
| STUDYID | 研究编号 | `CDISCPILOT01` |
| DOMAIN | 域名 | `DM` |
| USUBJID | **全研究唯一**受试者编号 | `01-701-1015` |
| --SEQ | 同一受试者内的记录序号 | `AESEQ = 1, 2, 3` |
| --DTC | ISO 8601 日期时间（字符） | `2014-01-03`、`2014-07-02T11:45` |
| --DY | 研究日 | `AESTDY = 2` |
| --TESTCD / --TEST | Findings 的检查项编码/名称 | `QSTESTCD = ACITM01` |
| --ORRES / --STRESC / --STRESN | 原始结果 / 标准化字符 / 标准化数值 | |

**研究日 `--DY` 规则（面试高频）**：以 `RFSTDTC`（首次给药日）为第 1 天，**没有第 0 天**。

- 日期 ≥ RFSTDTC：`DY = 日期 − RFSTDTC + 1`
- 日期 < RFSTDTC：`DY = 日期 − RFSTDTC`（筛选期为负数）

真实验证：受试者 01-701-1015，`RFSTDTC = 2014-01-02`，第一条 AE `AESTDTC = 2014-01-03` → `AESTDY = 2`；DM 的 `DMDTC = 2013-12-26` → `DMDY = −7`。

### 2.4 真实数据长什么样

**SDTM.DM（一人一行）**——注意 ARM 有 4 种值：

| DM.ARM | 受试者数 |
|---|---|
| Placebo | 86 |
| Xanomeline High Dose | 84 |
| Xanomeline Low Dose | 84 |
| Screen Failure | 52 |

**SDTM.EX（一人多行，每段给药一行）**：

| USUBJID | EXSEQ | EXTRT | EXDOSE | EXSTDTC | EXENDTC | VISIT |
|---|---|---|---|---|---|---|
| 01-701-1015 | 1 | PLACEBO | 0 | 2014-01-02 | 2014-01-16 | BASELINE |
| 01-701-1015 | 2 | PLACEBO | 0 | 2014-01-17 | 2014-06-18 | WEEK 2 |
| 01-701-1015 | 3 | PLACEBO | 0 | 2014-06-19 | 2014-07-02 | WEEK 24 |

**SDTM.AE（一个 AE 一行）**：

| USUBJID | AESEQ | AETERM | AEDECOD | AEBODSYS | AESTDTC | AESEV | AESER |
|---|---|---|---|---|---|---|---|
| 01-701-1015 | 1 | APPLICATION SITE ERYTHEMA | APPLICATION SITE ERYTHEMA | GENERAL DISORDERS AND ADMINISTRATION SITE CONDITIONS | 2014-01-03 | MILD | N |
| 01-701-1015 | 3 | DIARRHOEA | DIARRHOEA | GASTROINTESTINAL DISORDERS | 2014-01-09 | MILD | N |

- `AETERM`：研究者写的原话（verbatim）
- `AEDECOD`：MedDRA 编码后的首选术语 PT
- `AEBODSYS`：MedDRA 系统器官分类 SOC

> **小白提问：为什么 SDTM 不直接拿来分析？**
> 因为它缺“分析用”的东西：没有基线、没有变化值、没有分析人群标志、治疗组是字符且散落在 DM；AE 不知道是否“治疗期出现”。每个人每次分析都自己推导，就会每个人算出不一样的数——ADaM 就是为了解决这个问题。

---

## 3. ADaM：把数据变成“一步就能分析”

### 3.1 ADaM 的四个原则

1. **可追溯（Traceability）**：每个分析值都能追溯回 SDTM（甚至写明来源变量，如 ADTTE 的 `SRCDOM / SRCVAR / SRCSEQ`）。
2. **分析就绪（Analysis-ready / one PROC away）**：拿到数据后，一个 PROC（或一个函数）就能出结果，不需要再合并、再推导。
3. **有元数据**：Define-XML 写清楚每个变量怎么来的。
4. **可被统计软件直接读取**。

### 3.2 四种结构（必背）

| 结构 | 粒度 | 典型数据集 | 本仓库真实例子 |
|---|---|---|---|
| **ADSL** Subject-Level | 一人一行 | ADSL | 254 行 × 48 变量 |
| **BDS** Basic Data Structure | 一人 × 参数 × 时间点 一行 | ADLB、ADVS、ADQSxxx、ADEFF | ADQSADAS 12,463 行 |
| **BDS 的 TTE 形式** | 一人 × 参数 一行 | ADTTE | 254 行 |
| **OCCDS** Occurrence Data Structure | 一个事件/用药一行 | ADAE、ADCM、ADMH | ADAE 1,191 行 |

**每个研究必须有 ADSL**，其他 ADaM 数据集通常从 ADSL 合并人群标志和治疗组。

### 3.3 ADSL 关键变量

| 变量 | 含义 | 01-701-1015 的值 |
|---|---|---|
| TRT01P / TRT01PN | 第 1 期**计划**治疗（随机分到的） | Placebo / 0 |
| TRT01A / TRT01AN | 第 1 期**实际**治疗 | Placebo / 0 |
| TRTSDT / TRTEDT | 首次/末次给药日期 | 2014-01-02 / 2014-07-02 |
| TRTDUR | 治疗持续天数 = TRTEDT − TRTSDT + 1 | 182 |
| AGEGR1 | 年龄分组 | <65 |
| ITTFL / SAFFL / EFFFL | 意向治疗 / 安全性 / 疗效人群标志 | Y / Y / Y |
| COMP24FL | 完成第 24 周 | Y |

> **人群标志只用 Y/N（或 Y/空）**，这是 ADaM 的惯例。表格的分母就靠它们。

真实人群汇总（ADSL，按 TRT01P）：

| 人群 | Placebo | Xan Low | Xan High | 合计 |
|---|---|---|---|---|
| 随机化/ITT (ITTFL) | 86 | 84 | 84 | 254 |
| 安全性 (SAFFL) | 86 | 84 | 84 | 254 |
| 疗效 (EFFFL) | 79 | 81 | 74 | 234 |
| 完成第24周 (COMP24FL) | 60 | 28 | 30 | 118 |

一眼就能看到一个重要的临床事实：**高/低剂量组完成率只有约 1/3，远低于安慰剂组（60/86）**——后面 AE 表会告诉你为什么（皮肤不良事件导致停药）。

### 3.4 BDS 关键变量（最重要的一组）

| 变量 | 含义 |
|---|---|
| PARAM / PARAMCD | 分析参数（“分析的是什么”），如 `ACTOT` = ADAS-Cog(11) 总分 |
| AVAL / AVALC | 分析值（数值/字符） |
| AVISIT / AVISITN | 分析访视（经过窗口化的访视） |
| ADT / ADY | 分析日期 / 分析日 |
| BASE | 基线值 |
| CHG | 较基线变化 = AVAL − BASE |
| PCHG | 较基线变化百分比 |
| ABLFL | 基线记录标志 |
| ANL01FL | 分析记录标志（同一访视多条记录时选哪条） |
| DTYPE | 推导类型，如 `LOCF`（末次观测值结转）、`AVERAGE` |

真实例子（ADQSADAS，01-701-1015 的 ACTOT 总分）：

| AVISIT | ADY | AVAL | BASE | CHG | ABLFL | ANL01FL | DTYPE |
|---|---|---|---|---|---|---|---|
| Baseline | 1 | 13.0 | 13.0 |  | Y | Y |  |
| Week 8 | 63 | 8.0 | 13.0 | -5.0 |  | Y |  |
| Week 16 | 126 | 11.0 | 13.0 | -2.0 |  | Y |  |
| Week 24 | 168 | 8.0 | 13.0 | -5.0 |  | Y |  |

读法：ADAS-Cog 分数越高认知越差，这位受试者第 24 周比基线降低 5 分（改善）。
**基线那一行 CHG 为空**——基线和自己比没有意义。

LOCF 的真实影响：第 24 周疗效分析中，有 **14 / 32 / 33** 行（安慰剂/低/高）是 LOCF 填补出来的（`DTYPE = LOCF`）。这些行在 SDTM 里根本不存在，是 ADaM 新增的**派生记录**——这就是“ADaM 可以增加行”的典型例子。

### 3.5 OCCDS（ADAE）关键变量

| 变量 | 含义 |
|---|---|
| TRTA | 实际治疗（安全性分析用实际治疗） |
| ASTDT / ASTDY | 分析开始日期/日 |
| ASTDTF | 日期填补标志（AE 日期不全时会填补，例如只知道月份） |
| **TRTEMFL** | 治疗期出现的不良事件（TEAE）标志 |
| AOCCFL / AOCCPFL / AOCCSFL | 每人首次发生（任意 AE / 每个 PT / 每个 SOC）标志 |
| AESEV / AESER / AEREL | 严重程度 / 严重性 / 相关性 |

TEAE 的通用定义：**首次给药当天或之后开始**（或给药前就有、给药后加重）的 AE。不同 SAP 会有细节差异（例如末次给药后 +30 天），**以 SAP 为准**。

### 3.6 ADTTE（时间-事件）

| 变量 | 含义 | 01-701-1015 |
|---|---|---|
| PARAMCD | 参数 | TTDE（首次皮肤类事件时间） |
| STARTDT | 起点 | 2014-01-02（= TRTSDT） |
| ADT | 事件/删失日期 | 2014-01-03 |
| AVAL | 时间（天）= ADT − STARTDT + 1 | 2 |
| **CNSR** | 删失：**0 = 事件，1 = 删失** | 0 |
| SRCDOM / SRCVAR / SRCSEQ | 来源追溯 | ADAE / ASTDT / 1 |

> **CNSR 是反直觉的**：0 才是“发生了事件”。SAS `PROC LIFETEST` 里写 `time AVAL*CNSR(1);`，R 里 `Surv(AVAL, 1 - CNSR)`。新手 80% 会在这里写反。

---

## 4. TFL：最终交付给统计师、医学和监管的表/列表/图

TFL（也常写作 TLF / TLG）= **T**ables 表、**L**istings 列表、**F**igures 图。

| 类型 | 是什么 | 例子 |
|---|---|---|
| Table | 汇总统计 | 人口学表、AE 发生率表、疗效 ANCOVA 表 |
| Listing | 逐条列出明细 | 严重不良事件列表、死亡列表、方案偏离列表 |
| Figure | 图 | KM 曲线、均值随时间变化图、森林图 |

### 4.1 TFL 的生产流程

```text
SAP → TFL Shell（空表模板：标题、列、行、脚注、小数位）
    → 主程序员写程序 → 输出 RTF/PDF
    → QC 程序员独立写程序 → 比对（PROC COMPARE / diffdf）
    → 统计师审阅 → 医学审阅 → 定稿进 CSR
```

### 4.2 真实 Table 1：人口学与基线特征（ITT，按 TRT01P）

| 项目 | Placebo | Xan Low | Xan High | 合计 |
|---|---|---|---|---|
| N | 86 | 84 | 84 | 254 |
| 年龄 Mean (SD) | 75.2 (8.59) | 75.7 (8.29) | 74.4 (7.89) | 75.1 (8.25) |
| 年龄 Median | 76.0 | 77.5 | 76.0 | 77.0 |
| 年龄 Min, Max | 52, 89 | 51, 88 | 56, 88 | 51, 89 |
| 年龄组 <65 | 14 (16.3%) | 8 (9.5%) | 11 (13.1%) | 33 (13.0%) |
| 年龄组 65-80 | 42 (48.8%) | 47 (56.0%) | 55 (65.5%) | 144 (56.7%) |
| 年龄组 >80 | 30 (34.9%) | 29 (34.5%) | 18 (21.4%) | 77 (30.3%) |
| 性别 女 | 53 (61.6%) | 50 (59.5%) | 40 (47.6%) | 143 (56.3%) |
| 性别 男 | 33 (38.4%) | 34 (40.5%) | 44 (52.4%) | 111 (43.7%) |

要点：**数据源 ADSL，分母 = 该组 ITT 人数，按计划治疗 TRT01P 分组**。

### 4.3 真实 Table 2：TEAE 总览（安全性人群，按实际治疗 TRTA）

| 类别 | Placebo (N=86) | Xan Low (N=84) | Xan High (N=84) |
|---|---|---|---|
| 至少1个TEAE的受试者 | 65 (75.6%) | 77 (91.7%) | 76 (90.5%) |
| 至少1个严重TEAE | 0 (0.0%) | 1 (1.2%) | 2 (2.4%) |
| 至少1个重度TEAE | 5 (5.8%) | 16 (19.0%) | 8 (9.5%) |
| 因AE停止研究 (ADSL.DSRAEFL) | 8 (9.3%) | 44 (52.4%) | 40 (47.6%) |
| TEAE 事件数 | 281 | 412 | 433 |

**最重要的一个概念：受试者数 ≠ 事件数。** “n (%)” 里的 n 是**发生过该事件的人数**（同一个人得 3 次瘙痒只算 1 人），百分比的分母是 **安全性人群该组人数**（来自 ADSL，而不是 ADAE！——ADAE 里没有 AE 的人根本不在 ADAE 中）。

按 PT 发生率前 5：

| SOC | PT | Placebo | Xan Low | Xan High |
|---|---|---|---|---|
| SKIN AND SUBCUTANEOUS TISSUE DISORDERS | PRURITUS 瘙痒 | 8 (9.3%) | 21 (25.0%) | 26 (31.0%) |
| GENERAL DISORDERS AND ADMIN SITE CONDITIONS | APPLICATION SITE PRURITUS 用药部位瘙痒 | 6 (7.0%) | 22 (26.2%) | 22 (26.2%) |
| SKIN AND SUBCUTANEOUS TISSUE DISORDERS | ERYTHEMA 红斑 | 8 (9.3%) | 14 (16.7%) | 14 (16.7%) |
| GENERAL DISORDERS AND ADMIN SITE CONDITIONS | APPLICATION SITE ERYTHEMA | 3 (3.5%) | 12 (14.3%) | 15 (17.9%) |
| SKIN AND SUBCUTANEOUS TISSUE DISORDERS | RASH 皮疹 | 5 (5.8%) | 13 (15.5%) | 9 (10.7%) |

解读：透皮贴剂导致大量皮肤/用药部位反应 → 停药 → 完成率低。数据把一个完整的临床故事串起来了。

### 4.4 真实 Table 3：主要疗效（ADAS-Cog 第 24 周较基线变化，LOCF，疗效人群）

| 组别 | n | 基线 Mean (SD) | 第24周 Mean (SD) | CHG Mean (SD) |
|---|---|---|---|---|
| Placebo | 79 | 24.1 (12.19) | 26.7 (13.79) | 2.5 (5.80) |
| Xan Low | 81 | 24.4 (12.92) | 26.4 (13.18) | 2.0 (5.55) |
| Xan High | 74 | 21.3 (11.74) | 22.8 (12.48) | 1.5 (4.26) |

ANCOVA 模型：`CHG = 治疗 + 中心组(SITEGR1) + 基线(BASE)`

| 比较 | LS 均值差 | SE | 95% CI | p 值 |
|---|---|---|---|---|
| Xan Low vs Placebo | -0.47 | 0.82 | (-2.08, 1.15) | 0.569 |
| Xan High vs Placebo | -1.01 | 0.84 | (-2.66, 0.65) | 0.233 |

剂量-反应检验 p = 0.245 → **主要终点未达到统计学显著**。这与 CDISC Pilot 公开 CSR 的结论一致。

### 4.5 真实 Figure：KM 曲线（首次皮肤类不良事件时间）

![KM curve](generated/km_ttde.svg)

| 组别 | N | 事件数 | 删失数 | KM 中位时间（天） |
|---|---|---|---|---|
| Placebo | 86 | 29 | 57 | 未达到 |
| Xan Low | 84 | 62 | 22 | 33 |
| Xan High | 84 | 61 | 23 | 36 |

Log-rank χ² = 60.27，df = 2，p ≈ 8.2×10⁻¹⁴。
“未达到”的意思是安慰剂组生存曲线始终没掉到 0.5 以下，**不是**“没有数据”。

### 4.6 真实 Listing：严重不良事件（节选）

| TRTA | USUBJID | AGE | SEX | AEDECOD | ASTDT | ASTDY | AESEV | AEREL |
|---|---|---|---|---|---|---|---|---|
| Xanomeline High Dose | 01-709-1424 | 77 | M | SYNCOPE | 2013-03-07 | 5 | MODERATE | POSSIBLE |
| Xanomeline High Dose | 01-718-1371 | 69 | F | PARTIAL SEIZURES WITH SECONDARY GENERALISATION | 2013-06-02 | 38 | SEVERE | NONE |
| Xanomeline Low Dose | 01-718-1170 | 80 | F | SYNCOPE | 2013-10-12 | 27 | SEVERE | PROBABLE |

Listing 不做汇总，按 治疗组 → 受试者 → 日期 排序，便于医学逐例审阅。

### 4.7 分组变量怎么选（新手必错）

| 分析 | 人群 | 分组变量 | 原因 |
|---|---|---|---|
| 疗效（ITT 原则） | ITTFL / EFFFL | **计划** TRT01P / TRTP | 保持随机化的可比性 |
| 安全性 | SAFFL | **实际** TRT01A / TRTA | 看真正接受的药物带来的风险 |

本 Pilot 中计划=实际，所以数字一样；但在本仓库 v0.23/v0.24 的 pharmaverse 衍生数据中，有 **12 名受试者计划高剂量、实际低剂量**——这时用错变量，安全性分母会偏差最多 12 人、TEAE 率偏差最多 5.16 个百分点（详见 `docs/study_statistician_design_safety_governance_v0_24.md`）。

---

## 5. 实战：一个受试者从 SDTM 走到 TFL

以 **01-701-1015**（63 岁女性，安慰剂组）为例，串起全流程：

| 步骤 | 数据集 | 发生了什么 |
|---|---|---|
| 1 | SDTM.DM | ARM = Placebo，RFSTDTC = 2014-01-02，AGE = 63 |
| 2 | SDTM.EX | 3 段给药：2014-01-02 → 2014-07-02 |
| 3 | ADSL | TRTSDT = min(EXSTDTC) = 2014-01-02；TRTEDT = max(EXENDTC) = 2014-07-02；TRTDUR = 182；AGEGR1 = `<65`；SAFFL/ITTFL/EFFFL = Y |
| 4 | SDTM.AE → ADAE | 3 个 AE，ASTDY = 2/2/8，均 ≥ TRTSDT → TRTEMFL = Y；从 ADSL 带入 TRTA = Placebo |
| 5 | ADQSADAS | ACTOT 基线 13 → 第 24 周 8，CHG = −5 |
| 6 | ADTTE | 第 2 天发生用药部位红斑 → TTDE：AVAL = 2，CNSR = 0，SRCDOM = ADAE，SRCSEQ = 1 |
| 7 | TFL | 计入人口学表 Placebo 列 `<65` 那一格；计入 AE 表 “至少1个TEAE” 的 65 人之一；计入 ADAS-Cog 表 Placebo n = 79；KM 曲线第 2 天的那一个下降台阶 |

完整的逐表展示见 [`generated/real_data_examples.md` 第 3 节](generated/real_data_examples.md#3-一名受试者01-701-1015从-sdtm-到-adam-的完整追溯)。

> 练习：在 KM 图里找到 Placebo 组第 2 天的那个台阶，它就包含这位受试者。

---

## 6. QC：为什么要双人独立编程（真实差异案例）

制药行业标准做法：**主程序员（Production）和 QC 程序员各自独立读 Spec 写程序**，最后用 `PROC COMPARE`（SAS）或 `diffdf`（R）逐值比对，0 差异才能放行。

我们用真实数据做了一次“QC 程序员”：只看 SDTM，独立推导 ADSL 的 5 个变量，然后与 CDISC 官方 ADSL 比对：

| 变量 | 推导规则 | 一致 | 不一致 |
|---|---|---|---|
| AGEGR1 | <65 / 65-80 / >80 | 254 | 0 |
| SAFFL | 有任意 EX 记录 | 254 | 0 |
| TRTSDT | min(EXSTDTC) | 254 | 0 |
| TRTEDT | **v1：max(EXENDTC)** | 248 | **6** |
| TRTDUR | v1 | 248 | 6 |
| TRTEDT | **v2：末次 EX 的 EXENDTC 缺失时，用 DM.RFENDTC** | 254 | 0 |
| TRTDUR | v2 | 254 | 0 |

6 个差异受试者：01-704-1233、01-705-1018、01-705-1031、01-705-1303、01-705-1377、01-705-1382。
以 01-704-1233 为例：

| EXSEQ | EXSTDTC | EXENDTC |
|---|---|---|
| 1 | 2013-03-21 | 2013-04-04 |
| 2 | 2013-04-05 | **（空）** |

v1 取 max 得到 2013-04-04，但这位受试者显然 4 月 5 日之后仍在用药；官方 ADSL 用 RFENDTC = 2013-07-14 填补。

**这就是双人编程的价值**：差异不是“谁写错了代码”，而是 **Spec 没写清楚缺失日期怎么处理**。正确的处理流程是：

1. 记录差异 → 2. 查源数据 → 3. 与统计师确认规则 → 4. **更新 Spec** → 5. 双方按新 Spec 重跑 → 6. 比对 0 差异 → 7. 留下 QC 记录。

---

## 7. 代码示意：SAS / R(admiral) / Python

> 以下为教学示意，展示思路；完整可运行版本见 `scripts/build_cdisc_learning_examples.py`（Python）、`sas/derive_adsl_adae.sas`（SAS）、`R/`（R）。

### 7.1 SAS：从 EX 推导 TRTSDT / TRTEDT

```sas
data ex2;
  set sdtm.ex;
  exstdt = input(substr(exstdtc, 1, 10), yymmdd10.);
  exendt = input(substr(exendtc, 1, 10), yymmdd10.);
  format exstdt exendt date9.;
run;

proc sort data=ex2; by usubjid exstdt; run;

data trt;
  set ex2;
  by usubjid;
  retain trtsdt trtedt;
  if first.usubjid then do; trtsdt = exstdt; trtedt = .; end;
  trtedt = max(trtedt, exendt);
  if last.usubjid then do;
    if missing(exendt) then trtedt = .;   /* 末次记录未结束：交给 RFENDTC 规则 */
    output;
  end;
  keep usubjid trtsdt trtedt;
run;

data adsl;
  merge sdtm.dm(in=a where=(arm ne 'Screen Failure')) trt;
  by usubjid;
  if a;
  if missing(trtedt) then trtedt = input(substr(rfendtc, 1, 10), yymmdd10.);
  trtdur = trtedt - trtsdt + 1;
  length agegr1 $5;
  if age < 65 then agegr1 = '<65';
  else if age <= 80 then agegr1 = '65-80';
  else agegr1 = '>80';
  saffl = ifc(not missing(trtsdt), 'Y', 'N');
run;
```

### 7.2 SAS：AE 发生率（受试者数，分母来自 ADSL）

```sas
proc sql;
  create table denom as
    select trt01a as trta, count(distinct usubjid) as bign
    from adam.adsl where saffl = 'Y' group by trt01a;

  create table pt as
    select trta, aebodsys, aedecod, count(distinct usubjid) as n
    from adam.adae where saffl = 'Y' and trtemfl = 'Y'
    group by trta, aebodsys, aedecod;

  create table pt_pct as
    select a.*, b.bign, a.n / b.bign * 100 as pct format=5.1
    from pt a left join denom b on a.trta = b.trta;
quit;
```

### 7.3 R（pharmaverse/admiral 风格）

```r
library(admiral); library(dplyr)

adsl <- dm %>%
  filter(ARM != "Screen Failure") %>%
  derive_vars_merged(
    dataset_add = ex_ext,                 # 已用 derive_vars_dtm() 生成 EXSTDTM/EXENDTM
    by_vars     = exprs(STUDYID, USUBJID),
    new_vars    = exprs(TRTSDTM = EXSTDTM),
    order       = exprs(EXSTDTM, EXSEQ),
    mode        = "first"
  ) %>%
  mutate(
    AGEGR1 = case_when(AGE < 65 ~ "<65", AGE <= 80 ~ "65-80", TRUE ~ ">80"),
    SAFFL  = if_else(!is.na(TRTSDTM), "Y", "N")
  )

# KM：注意 CNSR 要反过来
library(survival)
fit <- survfit(Surv(AVAL, 1 - CNSR) ~ TRTA, data = adtte)
```

### 7.4 Python（pandas）：一行读懂“受试者数 vs 事件数”

```python
te = adae[(adae.SAFFL == "Y") & (adae.TRTEMFL == "Y")]
n_subjects = te.groupby("TRTA").USUBJID.nunique()   # 人数：65 / 77 / 76
n_events   = te.groupby("TRTA").size()              # 事件数：281 / 412 / 433
denom      = adsl[adsl.SAFFL == "Y"].groupby("TRT01A").size()  # 分母：86 / 84 / 84
```

---

## 8. 新手最常踩的 12 个坑

| # | 坑 | 正确做法 |
|---|---|---|
| 1 | AE 表分母用 ADAE 的人数 | 分母来自 **ADSL** 的人群标志 |
| 2 | 受试者数和事件数混用 | n(%) 用 `count(distinct USUBJID)` |
| 3 | 疗效表用实际治疗分组 | 疗效按计划（ITT），安全性按实际 |
| 4 | CNSR 写反 | ADaM 中 0=事件，1=删失 |
| 5 | 研究日算出第 0 天 | 没有 Day 0 |
| 6 | 基线行算 CHG | 基线行 CHG 为空（或按 SAP） |
| 7 | 字符日期直接比较大小 | 先转成数值日期（`ADT`），注意不完整日期 |
| 8 | 不完整日期直接丢弃 | 按 SAP 规则填补，并设 `--DTF` 标志 |
| 9 | 忘记筛选失败的人 | DM ≠ ADSL 人数（306 vs 254） |
| 10 | 同一访视多条记录随便取 | 用 `ANLzzFL` 明确选择规则 |
| 11 | 百分比四舍五入后总和不是 100% 就“修正” | 不要修正，按 shell 规定的小数位如实呈现 |
| 12 | 只看程序跑通没报错 | 看 log（WARNING / NOTE: uninitialized / merge 多对多），做 QC 比对 |

---

## 9. 术语表

| 术语 | 全称 | 中文 |
|---|---|---|
| CRF / eCRF | (electronic) Case Report Form | 病例报告表 |
| EDC | Electronic Data Capture | 电子数据采集系统 |
| SAP | Statistical Analysis Plan | 统计分析计划 |
| CSR | Clinical Study Report | 临床研究报告 |
| TEAE | Treatment-Emergent Adverse Event | 治疗期出现的不良事件 |
| SAE | Serious Adverse Event | 严重不良事件 |
| MedDRA | Medical Dictionary for Regulatory Activities | AE 编码词典（SOC/HLGT/HLT/PT/LLT） |
| WHODrug | WHO Drug Dictionary | 合并用药编码词典 |
| ITT / FAS / PP | Intent-to-Treat / Full Analysis Set / Per-Protocol | 意向治疗 / 全分析集 / 符合方案集 |
| LOCF | Last Observation Carried Forward | 末次观测值结转 |
| MMRM | Mixed Model for Repeated Measures | 重复测量混合模型 |
| ANCOVA | Analysis of Covariance | 协方差分析 |
| KM | Kaplan–Meier | 生存曲线估计 |
| Define-XML | — | 数据集元数据说明书 |
| ADRG / SDRG | Analysis/Study Data Reviewer's Guide | 分析/制表数据审阅指南 |
| P21 | Pinnacle 21 | 最常用的 CDISC 合规检查工具 |
| XPT | SAS Transport v5 | FDA 递交数据文件格式 |

---

## 10. 练习题（附答案）

**Q1.** DM 有 306 行，ADSL 只有 254 行，少的 52 人是谁？
<details><summary>答案</summary>筛选失败（ARM = Screen Failure）的受试者。他们签了知情同意出现在 DM 中，但没有随机化，不进入本研究的 ADSL。</details>

**Q2.** 某受试者 RFSTDTC = 2014-01-02，AE 开始于 2013-12-30，AESTDY = ？
<details><summary>答案</summary>−3（2013-12-30 − 2014-01-02 = −3，给药前没有 +1）。这条 AE 通常不是 TEAE（除非给药后加重）。</details>

**Q3.** 高剂量组 PRURITUS 共 26 人，但该 PT 的 TEAE 记录有 38 条，发生率表里写哪个？
<details><summary>答案</summary>发生率表写 26 (31.0%)，分母是安全性人群 84。事件数只在专门的“事件数”行/表中呈现。</details>

**Q4.** 为什么第 24 周 ADAS-Cog 分析有 234 人而不是 254 人？
<details><summary>答案</summary>分析人群是疗效人群 EFFFL = Y（79+81+74 = 234），即 ITT 中有基线以及至少一次基线后 ADAS-Cog 和 CIBIC+ 评估的受试者（以 SAP 定义为准）。</details>

**Q5.** ADTTE 中 CNSR = 1、AVAL = 180 表示什么？
<details><summary>答案</summary>该受试者在第 180 天被删失（直到观察结束都没有发生事件），不是“第 180 天发生事件”。</details>

**Q6.** 本数据中低剂量组 44 人因 AE 停止研究，而“至少1个TEAE”有 77 人。这两个数字能直接相减吗？
<details><summary>答案</summary>不能简单解释。两者来源不同（ADSL.DSRAEFL vs ADAE.TRTEMFL），回答的是两个不同的问题。用受试者级合并核对可以确认：全部 92 名因 AE 停止研究的受试者（8/44/40）都在 TEAE 受试者中，即 44 人是 77 人的子集——这种“交叉核对”本身就是一个好的 QC 习惯。</details>

**Q7.** 双人编程时 TRTEDT 有 6 人不一致，主程序员说“我的代码没错”，QC 程序员也说“我的没错”，怎么办？
<details><summary>答案</summary>回到 Spec 和源数据：这 6 人末次 EX 记录 EXENDTC 缺失，Spec 没规定填补规则。与统计师确认规则（如用 RFENDTC），更新 Spec 版本，双方重跑，比对 0 差异，留痕。</details>

---

## 11. 学习路线与资源

**4 周入门路线**

| 周 | 学什么 | 本仓库练习 |
|---|---|---|
| 1 | 临床试验基础 + SDTM 域与变量 | 打开 `cache/learning/dm.csv`、`ae.csv`、`ex.csv`，对照本手册第 2 章 |
| 2 | ADaM：ADSL、BDS、OCCDS、ADTTE | 读 `generated/real_data_examples.md` 第 3 节，自己复算 01-701-1015 |
| 3 | TFL：人口学表、AE 表、疗效表、KM 图 | 改脚本：把人口学表加上 BMI；把 AE 表改成按 SOC 汇总 |
| 4 | QC 与递交：Define-XML、P21、XPT | 读 `docs/independent_programming_qc.md`、`docs/cdisc_standards_validation.md` |

**官方与开源资源**

- CDISC 官网标准下载：<https://www.cdisc.org/standards>（SDTMIG、ADaMIG 需免费注册）
- CDISC Pilot 项目（本手册数据来源）：<https://github.com/cdisc-org/sdtm-adam-pilot-project>
- pharmaverse（R 开源临床编程生态：admiral、metacore、xportr、rtables、Tplyr）：<https://pharmaverse.org>
- FDA Study Data Technical Conformance Guide（递交技术要求）
- Pinnacle 21 Community（免费合规检查工具）

**复现本手册所有数字**

```bash
pip install -r requirements.txt
python scripts/build_cdisc_learning_examples.py
# 输出：docs/learning/generated/real_data_examples.md / real_data_metrics.json / km_ttde.svg
```
