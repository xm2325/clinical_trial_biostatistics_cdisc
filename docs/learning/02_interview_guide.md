# CDISC / ADaM / TFL 面试讲解版（真实数据支撑）

> 目标岗位：统计程序员（Statistical Programmer / SAS Programmer）、临床数据科学、生物统计师（偏编程）。
> 用法：先背 **第 1 章的 30 秒 / 2 分钟讲解**，再刷 **第 2–7 章高频题**，最后准备 **第 8 章项目故事**。
> 所有数字来自 CDISC 官方 Pilot 研究 CDISCPILOT01（GitHub 公开数据），可用 `python scripts/build_cdisc_learning_examples.py` 复现。
> 入门讲解见 [`01_beginner_handbook.md`](01_beginner_handbook.md)。

**答题公式**：**定义 → 为什么 → 真实例子（带数字）→ 坑/经验**。面试官最想听到的是第 3、4 步——它证明你真的摸过数据。

---

## 1. 开场讲解模板

### 1.1 30 秒版：“请介绍一下 CDISC 数据流”

> 临床试验数据在 EDC 里按 CDASH 采集，然后映射成 **SDTM**——它按域组织，忠实记录发生了什么，比如 DM、AE、EX。
> 在 SDTM 基础上推导 **ADaM**——为分析服务，包括一人一行的 ADSL、按参数和访视组织的 BDS、事件类的 OCCDS，强调可追溯和“一个 PROC 就能分析”。
> 最后由 ADaM 生成 **TFL**——表、列表、图，进入 CSR。全程用 Define-XML 描述元数据，用 Pinnacle 21 做合规检查，双人独立编程做 QC。

### 1.2 2 分钟版：用一个真实受试者讲完全流程

> 我用 CDISC 官方 Pilot 研究练过完整链路——这是一个阿尔茨海默病 Xanomeline 贴剂对比安慰剂的试验。
>
> **SDTM 层**：DM 有 306 人，其中 52 人筛选失败；以受试者 01-701-1015 为例，DM 里她的 RFSTDTC 是 2014-01-02，EX 里有 3 段给药记录，AE 里有 3 条不良事件。
>
> **ADaM 层**：ADSL 只保留 254 名随机化受试者。我从 EX 推导 TRTSDT/TRTEDT，算出她的治疗时长 182 天，年龄 63 归到 `<65` 组，打上 SAFFL/ITTFL/EFFFL。ADAE 中她第 2 天出现用药部位红斑，ASTDY=2，TRTEMFL=Y。ADQSADAS 是 BDS 结构，她的 ADAS-Cog 总分基线 13，第 24 周 8，CHG=−5。ADTTE 里她“首次皮肤事件时间”AVAL=2、CNSR=0，并且通过 SRCDOM/SRCSEQ 追溯回 ADAE 第 1 条记录。
>
> **TFL 层**：人口学表 ITT 按计划治疗分组；AE 表安全性人群按实际治疗分组，分母从 ADSL 取——安慰剂/低/高 TEAE 发生率 75.6%/91.7%/90.5%；主要疗效 ANCOVA 剂量反应 p=0.245，未达显著；KM 显示两个剂量组首次皮肤事件中位时间 33 和 36 天，安慰剂未达到中位。这些结果和 Pilot 公开 CSR 一致。
>
> **QC**：我只用 SDTM 独立复算 ADSL，与官方 ADSL 比对，发现 6 人 TRTEDT 不一致，根因是末次给药记录的结束日期缺失、Spec 没写填补规则；补上 “用 RFENDTC 填补” 后 254/254 全部一致。

> 💡 这一段的杀伤力在于：**每一句都有具体变量名 + 具体数字**，而且有一个“发现问题 → 定位根因 → 解决”的 QC 故事。

---

## 2. 基础概念题

**Q1. SDTM 和 ADaM 的区别？**
| 维度 | SDTM | ADaM |
|---|---|---|
| 目的 | 标准化呈现收集到的数据 | 支持统计分析 |
| 推导 | 极少（--DY、AGE 等） | 大量（基线、CHG、人群标志、填补） |
| 结构 | 按域（DM、AE、LB…） | ADSL / BDS / OCCDS |
| 能否加行 | 不能凭空加 | 可以（如 LOCF 行、平均值行） |
| 使用者 | 审评员看“发生了什么” | 统计师复现“结果怎么算的” |

真实例子：ADQSADAS 中第 24 周有 14/32/33 行 `DTYPE=LOCF` 的派生记录，SDTM.QS 中不存在。

**Q2. 为什么要有 ADaM，直接用 SDTM 分析不行吗？**
可以但不应该：①每张表都重复推导，不同程序员结果不一致；②审评员无法复现；③可追溯性差。ADaM 的核心价值是 **“推导一次、处处复用、可追溯、可复现”**。

**Q3. ADaM 的基本原则？**
可追溯、分析就绪（one PROC away）、附元数据（Define-XML）、可被常用软件读取。

**Q4. ADaM 有哪几种结构？**
ADSL（一人一行）、BDS（一人×参数×时间点，ADTTE 是 BDS 的时间-事件用法）、OCCDS（ADAE/ADCM/ADMH），以及不符合上述的 OTHER。每个研究必须有 ADSL。

**Q5. Define-XML 是什么？里面有什么？**
数据集的“机器可读说明书”：数据集列表、变量（名称、标签、类型、长度）、受控术语 Codelist、Value-Level Metadata、推导方法（Methods/Comments）、来源（Origin），ADaM 还可含 Analysis Results Metadata。随数据一起递交。

**Q6. ADRG 是什么？**
Analysis Data Reviewer's Guide，给审评员看的“导读”：分析数据集概述、特殊推导、人群定义、P21 未解决问题的解释等。SDTM 对应 SDRG（cSDRG）。

---

## 3. SDTM 题

**Q7. SDTM 有哪几类域？各举例。**
Special-Purpose（DM、SE、SV、CO）、Interventions（EX、CM、EC、PR）、Events（AE、DS、MH、DV）、Findings（LB、VS、QS、EG、PE），以及 Trial Design（TA、TE、TV、TI、TS）。

**Q8. --DY 怎么算？**
以 RFSTDTC 为第 1 天，没有第 0 天。真实验证：01-701-1015 的 RFSTDTC=2014-01-02，AE 开始 2014-01-03 → AESTDY=2；DM 采集日 2013-12-26 → DMDY=−7。

**Q9. AETERM、AEDECOD、AEBODSYS 的区别？**
研究者原文（verbatim）/ MedDRA 首选术语 PT / MedDRA 系统器官分类 SOC。表格通常按 SOC → PT 汇总。

**Q10. SUPPQUAL 是什么？什么时候用？**
标准域放不下的非标准变量（Non-Standard Variables）放在 SUPP--（如 SUPPAE），用 RDOMAIN/USUBJID/IDVAR/IDVARVAL/QNAM/QVAL 关联父记录。ADaM 中常把需要的 QNAM 合并回来。（SDTMIG v3.4 起也允许在部分场景用 NSV 直接放主域，以监管要求为准。）

**Q11. RFSTDTC 和 RFXSTDTC 的区别？**
RFSTDTC 是申办方定义的参考开始日期（常为首次给药），RFXSTDTC 明确为首次研究药物暴露日期。两者常相同，但定义不同，研究日以 RFSTDTC 为基准。

**Q12. 为什么 DM 和 ADSL 人数不同？**
真实数据：DM 306 人（含 Screen Failure 52 人），ADSL 254 人。DM 包含所有签署知情同意者，Pilot 的 ADSL 只包含随机化受试者（有的研究 ADSL 也包含筛选失败，看 SAP）。

---

## 4. ADaM 题

**Q13. TRT01P 和 TRT01A 的区别？什么时候用哪个？**
计划（随机）治疗 vs 实际治疗。**疗效按计划（ITT 原则，保护随机化），安全性按实际**（反映真实暴露）。
加分回答：在本仓库 v0.23/v0.24 的 pharmaverse 衍生数据中有 12 人计划高剂量、实际低剂量。若安全性误用计划治疗，组分母最多偏 12 人、TEAE 发生率最多偏 5.16 个百分点；而疗效 MI 必须按计划治疗分组，否则破坏随机化。**变量选择跟着统计问题走。**

**Q14. ADSL 必须有哪些变量？**
STUDYID、USUBJID、SUBJID、SITEID、AGE、AGEU、SEX、RACE、ARM、ACTARM、TRT01P、TRT01A（及 N 版本）、人群标志（如 SAFFL/ITTFL）、TRTSDT/TRTEDT 等（具体以 ADaMIG 的 Req/Cond 为准）。

**Q15. 讲讲 BDS 的 AVAL、BASE、CHG、ABLFL、ANL01FL、DTYPE。**
见入门手册 3.4。真实例子：01-701-1015 ACTOT 基线 13（ABLFL=Y），Week 24 AVAL=8，CHG=−5，ANL01FL=Y。
**坑**：基线行 CHG 为空；BASE 要从 ABLFL=Y 那行取并带到同一 PARAMCD 的所有行；同一访视多条要靠 ANL01FL 选一条。

**Q16. 基线怎么定义？**
通常为首次给药前最后一次非缺失评估（`ADT <= TRTSDT`），具体以 SAP 为准；如何处理同日多条、计划外访视都要写进 Spec。

**Q17. 访视窗口（windowing）是什么？**
实际访视日期常偏离计划，按 ADY 落入的窗口分配 AVISIT。Pilot 的 ADQSADAS 有 AWRANGE/AWTARGET/AWTDIFF/AWLO/AWHI 记录窗口信息；窗口内多条时按“离目标日最近”等规则用 ANL01FL 选。

**Q18. TRTEMFL 怎么推导？**
一般：`ASTDT >= TRTSDT`（且 `<= TRTEDT + n 天`，按 SAP），或给药前开始但给药后加重。AE 开始日期不完整时先按规则填补（ASTDTF 记录填补级别），**填补规则应偏向“保守地算作 TEAE”**。

**Q19. 不完整日期怎么填补？**
常见：开始日期缺日→取当月 1 日，但若同月同年已给药则取 TRTSDT；缺月日→1 月 1 日（同理比较 TRTSDT）；结束日期缺日→当月最后一天。设置 `ASTDTF='D'/'M'/'Y'`。具体以 SAP 为准。

**Q20. ADTTE 的 CNSR 是什么？怎么用？**
0 = 事件，1 = 删失（反直觉）。SAS：`time AVAL*CNSR(1);`；R：`Surv(AVAL, 1 - CNSR)`。真实数据：TTDE 事件数 29/62/61，删失 57/22/23。还应有 EVNTDESC/CNSDTDSC 描述以及 SRCDOM/SRCVAR/SRCSEQ 追溯。

**Q21. LOCF 有什么问题？**
假设缺失后值保持不变，可能偏倚且低估方差；现在主流用 MMRM（MAR 假设）+ 多重填补/参考基准填补（J2R、CR）做敏感性分析，并与 ICH E9(R1) 估计目标（Estimand）对齐。真实数据：第 24 周 LOCF 行 14/32/33，剂量组远多于安慰剂——因为剂量组停药多，**缺失不是随机的**，这正是 LOCF 被质疑的地方。（本仓库 v0.11–v0.24 有完整的 MMRM / MI / MNAR 敏感性分析示例。）

**Q22. 什么是 PARAMCD 的“一个参数一个含义”原则？**
同一个 PARAMCD 的 AVAL 必须单位、含义一致；不同单位/不同推导（如 LOCF 与 OC）要么用不同 PARAMCD，要么用 DTYPE 区分派生记录。

---

## 5. TFL 题

**Q23. AE 表的分母从哪里来？**
**ADSL**（`SAFFL='Y'` 按 TRT01A 计数），而不是 ADAE——ADAE 只含有 AE 的人。真实：安全性 N = 86/84/84；若错用 ADAE 的人数，分母会变成 69/77/79（ADAE 只含有过 AE 的人），安慰剂 TEAE 发生率会从 75.6% 虚高到 94.2%。

**Q24. 受试者数 vs 事件数？**
`count(distinct USUBJID)` vs `count(*)`。真实：TEAE 受试者 65/77/76 人，事件 281/412/433 条；高剂量 PRURITUS 26 人、38 条记录。

**Q25. AE 表按 SOC/PT 汇总时，SOC 行的人数怎么算？**
该 SOC 下任一 PT 发生过的**人数**（去重），不是各 PT 人数之和。同理“任何 TEAE”行不是各 SOC 之和。

**Q26. 如何做 TFL 的 QC？**
独立编程得到数值数据集 → `PROC COMPARE`（或 R `diffdf`）比对数值 → 再人工核对格式（标题、脚注、小数位、排序、分页）→ 审阅 log（无 ERROR/WARNING/uninitialized/多对多 merge）→ 留下 QC 记录与签字。

**Q27. 人口学表中的统计量怎么规定小数位？**
通常：原始数据精度 d，则 Mean/Median 保留 d+1，SD 保留 d+2，Min/Max 保留 d；百分比 1 位小数。以 Shell 为准。真实：年龄整数 → Mean 75.2，SD 8.59。

**Q28. 讲一下主要疗效表是怎么得到的。**
ADQSADAS，`PARAMCD='ACTOT'`、`AVISIT='Week 24'`、`EFFFL='Y'`、`ANL01FL='Y'`（含 LOCF 行），ANCOVA：`CHG = TRTP + SITEGR1 + BASE`。真实：n=234，Low vs Pbo −0.47（95% CI −2.08, 1.15），High vs Pbo −1.01（−2.66, 0.65），剂量反应 p=0.245。
SAS 示意：
```sas
proc glm data=adqs;
  where paramcd='ACTOT' and avisit='Week 24' and efffl='Y' and anl01fl='Y';
  class trtpn sitegr1;
  model chg = trtpn sitegr1 base / solution;
  lsmeans trtpn / diff cl pdiff;
run;
```

**Q29. KM 图要注意什么？**
CNSR 方向；时间单位；风险集表（number at risk）；中位数“未达到”的写法（NE / Not reached）；删失标记；组别颜色与图例；log-rank / Cox HR 写在图注。真实：Placebo 中位未达到，Low 33 天，High 36 天，log-rank p≈8.2×10⁻¹⁴。

**Q30. Listing 和 Table 的区别？为什么还要 Listing？**
Listing 逐条展示不汇总，供医学审阅个例（如 SAE、死亡、方案偏离）。真实：SAE 仅 0/1/2 人，监管一定会逐例看。

---

## 6. QC、合规与递交题

**Q31. 什么是双人独立编程？发现差异怎么处理？**
Production 和 QC 各自根据 Spec 独立编程后比对。真实案例（必讲）：
- 现象：独立复算 ADSL 的 TRTEDT，254 人中 6 人与官方不一致。
- 定位：6 人末次 EX 记录 EXENDTC 为空，“取 max”会落到前一段的结束日期。
- 根因：Spec 没规定开放式给药记录的处理。
- 解决：与统计师确认 “末次记录无结束日期时用 DM.RFENDTC”，更新 Spec，双方重跑 → 254/254 一致。
- 经验：**差异往往暴露 Spec 歧义，而不是单纯的代码 bug；解决方案必须落在 Spec 上并留痕。**

**Q32. Pinnacle 21 报错/警告怎么处理？**
分级（Reject/Error/Warning/Notice）→ 能修的修（数据或元数据问题）→ 不能修的（数据本身如此、标准限制）在 ADRG/SDRG 中逐条解释。不要为了消除警告去篡改真实数据。

**Q33. XPT v5 有哪些限制？**
数据集名和变量名 ≤ 8 字符；变量标签 ≤ 40 字符；字符变量长度 ≤ 200；数据集标签 ≤ 40。FDA 还要求单个文件过大时拆分（以最新 Technical Conformance Guide 为准）。Dataset-JSON 是 CDISC 推出的替代格式。

**Q34. 什么是 Controlled Terminology？举例。**
受控术语，规定变量可取值。例如 SEX：M/F/U/UNDIFFERENTIATED；AESEV：MILD/MODERATE/SEVERE；NY：Y/N。CT 每季度更新，研究需锁定版本并在 Define-XML 中声明。

**Q35. 你如何保证程序的可追溯和可复现？**
Spec 版本化；程序头注释（目的、输入、输出、修改历史）；固定数据版本（本仓库用固定 git commit + SHA256 哈希）；自动化运行与日志检查；输出与 Spec/Shell 的追溯矩阵（本仓库 `spec/analysis_traceability.csv`）。

---

## 7. 场景题（区分初级和中级的关键）

**S1. 统计师说“AE 表 Placebo 的 TEAE 发生率和上次 dry run 差了 1 个人”，你怎么查？**
1）比较两次数据快照的 ADSL 分母是否变化；2）找出差异受试者（两次 TEAE 受试者集合求差）；3）看该受试者的 AE 日期是否被更新/填补规则是否改变/TRTSDT 是否改变；4）确认是数据变化还是程序变化；5）记录并告知统计师。

**S2. 发现两个剂量组完成率只有约 1/3（28/84、30/84），而安慰剂 60/86，你会提醒什么？**
这会影响疗效分析：缺失不随机（因 AE 停药 44/40 vs 8），LOCF 结论可能偏倚；建议按 Estimand 框架明确伴发事件策略，并提供 MMRM、参考基准多重填补等敏感性分析。（统计师岗位的加分回答。）

**S3. 同一受试者同一访视有两条 ADAS-Cog 记录怎么办？**
看 SAP：通常取离目标日最近的，若距离相同取后一个/取均值；用 ANL01FL 标记被选中的记录，**不要删除记录**，保持可追溯。

**S4. 医学要求临时加一张“按年龄组的 TEAE 表”，但 SAP 没写，怎么办？**
可以做，但要标注为 post-hoc / ad hoc 分析；先确认分组定义（用 ADSL.AGEGR1：<65/65-80/>80）、人群和分母；走变更控制，不改动已定稿的主表。

**S5. Spec 和 SAP 冲突怎么办？**
SAP 是上位文件。停止编程 → 记录冲突 → 与统计师确认 → 更新 Spec（或 SAP 修订）→ 再编程。绝不自己“猜一个”。

---

## 8. 项目故事（STAR 法，基于本仓库）

> ⚠️ 诚实边界：本仓库是**基于公开数据的个人作品集**，不是申办方/CRO 生产项目、不是正式递交。面试时请如实说明，例如“我用 CDISC 官方 Pilot 数据独立完成了……”。夸大经验是面试大忌，诚实 + 细节反而更加分。

**故事 1：独立复算 ADSL 发现 Spec 歧义**
- S：用 CDISC Pilot 公开 SDTM，想验证自己能否复现官方 ADSL。
- T：独立推导 AGEGR1、SAFFL、TRTSDT、TRTEDT、TRTDUR 并与官方比对。
- A：Python 编程 + 自动比对；发现 6/254 人 TRTEDT 不一致；逐例查 EX 发现末次给药 EXENDTC 缺失；补充 RFENDTC 填补规则。
- R：254/254 全部一致；把规则沉淀为可执行脚本（`scripts/build_cdisc_learning_examples.py`）。

**故事 2：同一组 12 名受试者，疗效和安全性的分组答案不同**
- S：pharmaverse 衍生数据中 12 人计划高剂量、实际低剂量。
- T：确定疗效多重填补和安全性汇总分别应该用哪个治疗变量。
- A：疗效 MI 改用计划治疗（TRT01P）分组，安全性坚持实际治疗（TRT01A），并量化误用的影响。
- R：MI 目标人群从 182/158 修正为 170/170；安全性误用最多偏差 5.16 个百分点；写成受控规则与 QC 门槛（见 `docs/randomised_treatment_assignment_repair.md`）。

**故事 3：跨语言 QC（SAS / R / Python）**
- 本仓库在 SAS OnDemand for Academics 实际运行 SAS 程序，与 Python/R 结果对账，45/45 检查通过（ADSL、ADAE、TEAE `PROC FREQ`、第 24 周 `PROC MIXED` MMRM 与 R `mmrm` 估计值/SE 一致）。见 `docs/bms_statistical_programming_v0_26.md`。

---

## 9. 一页速记卡（面试前 10 分钟看）

```text
链路     CDASH → SDTM（事实）→ ADaM（分析）→ TFL（结论）→ CSR；Define-XML + ADRG + P21
SDTM     4 类：Special(DM) / Interventions(EX,CM) / Events(AE,DS,MH) / Findings(LB,VS,QS,EG)
--DY     没有 Day 0；RFSTDTC = Day 1
ADaM     ADSL(一人一行) / BDS(人×参数×时点) / OCCDS(事件) ；ADTTE = BDS 时间事件用法
分组     疗效 TRT01P/TRTP（ITT），安全 TRT01A/TRTA
分母     来自 ADSL 人群标志，不来自 ADAE
计数     受试者 = count(distinct USUBJID)；事件 = count(*)
CNSR     0 = 事件，1 = 删失
BDS      AVAL BASE CHG ABLFL ANL01FL DTYPE AVISIT PARAMCD
XPT      名 ≤8，标签 ≤40，字符 ≤200
真实数字 DM 306 / ADSL 254 / EFFFL 234
         TEAE 65(75.6%) / 77(91.7%) / 76(90.5%)，事件 281/412/433
         ADAS-Cog Wk24 剂量反应 p=0.245；High vs Pbo −1.01 (−2.66, 0.65)
         TTDE 中位 NR / 33 / 36 天，log-rank p≈8e-14
         QC：TRTEDT 6/254 不一致 → 末次 EXENDTC 缺失 → RFENDTC 填补 → 254/254
```

---

## 10. 反问面试官（显得专业）

1. 团队目前 SAS 和 R（pharmaverse/admiral）的比例？有没有向 R 或 Dataset-JSON 迁移的计划？
2. TFL QC 是全部双人独立编程，还是按风险分级（关键表双编、其他表代码审阅）？
3. Spec 和 Define-XML 是用什么工具维护的（Excel、P21 Enterprise、metacore）？
4. 新人入职一般先从 SDTM、ADaM 还是 TFL 做起？
