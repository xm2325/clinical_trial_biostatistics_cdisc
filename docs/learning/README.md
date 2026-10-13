# CDISC / ADaM / TFL 学习专区（真实数据）

| 文件 | 适合谁 | 内容 |
|---|---|---|
| [01_beginner_handbook.md](01_beginner_handbook.md) | 小白 / 转行 / 应届 | 从零讲清 CDISC → SDTM → ADaM → TFL，配真实数据、代码示意、常见坑、练习题 |
| [02_interview_guide.md](02_interview_guide.md) | 准备统计编程 / 生统面试 | 30 秒 & 2 分钟讲解模板、35 道高频题、5 道场景题、STAR 项目故事、速记卡 |
| [generated/real_data_examples.md](generated/real_data_examples.md) | 想核对数字的人 | 脚本自动生成的全部真实表格、受试者追溯、QC 比对和 KM 图 |

## 数据来源（GitHub 公开、固定 commit）

- SDTM：[`pharmaverse/pharmaversesdtm`](https://github.com/pharmaverse/pharmaversesdtm) @ `7ec53ea` — DM / EX / DS / AE
- ADaM：[`cdisc-org/sdtm-adam-pilot-project`](https://github.com/cdisc-org/sdtm-adam-pilot-project) @ `667511d` — ADSL / ADAE / ADQSADAS / ADTTE（CDISCPILOT01，Dataset-JSON）

## 复现

```bash
pip install -r requirements.txt
python scripts/build_cdisc_learning_examples.py      # 下载到 cache/learning/，重新生成 generated/
```

> 说明：这是基于公开数据的学习材料，不代表任何申办方/CRO 的生产标准；具体规则（TEAE 窗口、日期填补、基线定义等）一律以各研究的 SAP 和 Spec 为准。
