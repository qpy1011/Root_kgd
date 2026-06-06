# Elevator KG Sources

## Local Data

- `2025年200台电梯困人工单数据.xlsx`: used only for work-order id, elevator registration code, place/site type, maintenance unit, manufacturer, fault reason, trapped-person count, rescue level, and rescue time. Personal names and phone numbers are not exported.
- `fau_rep.xls`: used for aggregate fault phenomenon, fault cause, fault location, replacement-part type, trapped-person and source statistics.

## Web References

- [市场监管总局关于 TSG T7001-2023 与 TSG T7008-2023 的解读](https://www.samr.gov.cn/xw/zj/art/2023/art_971676b200df4c529d1971911f5927a7.html): 用于监管规则节点和自行检测/定期检验语义。
- [市场监管总局 GB/T 7588.1-2020/GB/T 7588.2-2020 解读](https://www.samr.gov.cn/sps/sjdt/gzdt/art/2023/art_72c228af3bd144c584a682322159199d.html): 用于制动器、上行超速、轿厢意外移动、安全回路和救援检修相关节点。
- [TSG T5002-2017 电梯维护保养规则](https://www.haian.gov.cn/hascjgj/sgjf/content/a8589ce7-7138-4c77-ab35-104a47e910ed.html): 用于半月、季度、半年、年度维保范围和处置动作语义。
- [杭州市 96333 电梯应急处置通报](https://www.hangzhou.gov.cn/art/2020/8/28/art_812262_55518767.html): 用于困人、门系统、人为原因、外部原因等故障类别证据。
- [泰安市 96333 电梯应急处置服务平台数据](http://scjgj.taian.gov.cn/art/2017/10/9/art_201048_8273969.html): 用于维保救援、人员原因、停电、进水等处置语义。
- [日照市 96333 电梯应急处置中心运行情况通报](http://www.rizhao.gov.cn/art/2022/1/25/art_39601_10297757.html): 用于困人原因的门系统、外部原因和人为原因统计语义。
- [Graph-based / GNN elevator fault diagnosis literature](https://pmc.ncbi.nlm.nih.gov/articles/PMC12788203/): 用于后续把该 KG 接入 GNN 异常追溯的技术背景。

The web references provide domain priors; local Excel data provides observed evidence and edge weights.