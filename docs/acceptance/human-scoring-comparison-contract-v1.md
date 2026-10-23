# 人工评分对照契约 v1

## 目的

建立可复核的人类基准，之后才可以讨论“评分与人工判断的一致性”。这不是人工改判率，也不是生产评分准确率。

## 固定样本与盲法

- 来源固定为 `evals/datasets/evaluation_discrimination_v1.jsonl` 的全部 12 条（4 主题 × low/mid/high）。
- 评审表 `evals/reviews/scoring-human-comparison-v1/worksheet.jsonl` 仅含 blind id、题目、回答和四维 rubric；不含模型输出、已有标签、分档和期望复核结果。
- `author_key.json` 只供独立比对程序使用，评审人不得查看。评审结果须由至少两名独立人工评审分别填写。

## 人工评审输出

每名评审对每条填写 correctness、completeness、reasoning、communication（每项 0–5）和 `needs_review`，再提供一句理由。总分由比较器重算，禁止手填总分。

## 预声明判断

1. 先测两名人工评审在总分上的一致性与 `needs_review` 一致性；一致性不足时不比较模型。
2. 人工一致后，才将经裁决的人类分数与固定模型运行报告逐条比对，报告 MAE、分档顺序与复核路由一致性。
3. 样本数为 12，只能称为“小样本对照观察”，不得外推为生产评分准确率。

## 人工介入点

需要两名评审独立填写 worksheet，随后由你或指定裁决人处理分歧。代码可以生成、校验和比较文件，但不能伪造人工标签。
