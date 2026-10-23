# 多模型盲审校准观察（2026-10-23）

## 结论

两份独立模型输出对固定 12 条 blind 样本的粗粒度判断完全一致：

| 指标 | 结果 |
|---|---:|
| 样本数 | 12 |
| 质量标签一致（差／一般／好） | 12 / 12 |
| 是否需要复核一致 | 12 / 12 |
| 两个字段同时一致 | 12 / 12 |

用户报告本次结果来自两个不同模型（`deepseek-v4.1-flash` 与 `step-5-preview`）；粘贴文本未保留“哪一份输出对应哪一个模型”的可靠字段，因此原始文件只标记为 Model A / Model B，未擅自绑定模型名。

## 输入与复现

- 盲审题面：`docs/evaluations/single-reviewer-coarse-calibration-form.md`
- Model A 原始盲审输出：`evals/reviews/scoring-human-comparison-v1/model-a-blind-output-20261023.jsonl`
- Model B 原始盲审输出：`evals/reviews/scoring-human-comparison-v1/model-b-blind-output-20261023.jsonl`
- 机器比对明细：`docs/evaluations/multi-model-blind-calibration-20261023.json`
- 比对器：`scripts/compare_blind_calibration.py`

运行比对：

```powershell
.\.venv\Scripts\python.exe scripts\compare_blind_calibration.py `
  evals\reviews\scoring-human-comparison-v1\model-a-blind-output-20261023.jsonl `
  evals\reviews\scoring-human-comparison-v1\model-b-blind-output-20261023.jsonl `
  --output docs\evaluations\multi-model-blind-calibration-20261023.json
```

## 可以与不可以说

可以说：对一组没有暴露作者标签、已有分数和预期分档的固定样本，两个不同模型给出了完全相同的粗粒度质量判断与复核判断。

不能说：这证明了人工评分一致性、生产评分准确率，或两个模型独立覆盖了所有题型。模型可能共享训练语料、推理模式或提示词偏差；并且本样本的质量梯度较清晰，不能外推到边界答案。

## 与人工校准的关系

这份报告是“多模型盲审趋同”证据，不能替代 `docs/acceptance/human-scoring-comparison-contract-v1.md` 中的人工对照。若未来获得一位真实评审，只需填轻量表单，即可作为独立的单评审粗粒度校准补充。
