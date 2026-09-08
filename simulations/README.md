# Simulation status

`ablation_study.py` is retained solely for historical reproducibility. It
evaluates every query against a corpus containing that same query and obtains a
prediction from the retrieved corpus label. This leaks test labels and invalidates
its F1 values for paper use.

Do not report values from that script, including any previously reported 91.8%.
Use the independent claim benchmark workflow in `docs/EVALUATION_PROTOCOL.md`.
