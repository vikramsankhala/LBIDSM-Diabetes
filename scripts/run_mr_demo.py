"""Demonstrate the MR target filter on SIMULATED data. Plumbing only; no scientific claim."""
from lbidsm import mr

d = mr.synthetic_mr_data(12, true_beta=0.4, seed=12)
res = mr.target_filter(d, region=mr.synthetic_locus(shared=True, seed=12),
                       disease_instruments=mr.synthetic_mr_data(10, 0.0, seed=13))
print(res["verdict"]); print(res["checks"]); print(res["mr"].round(3).to_string(index=False))
print("colocalisation:", {k: round(v, 3) if isinstance(v, float) else v for k, v in res["colocalisation"].items()})
strata = mr.stratified_mr({"endotype_A": mr.synthetic_mr_data(10, 0.6, seed=8),
                           "endotype_B": mr.synthetic_mr_data(10, 0.0, seed=9)})
print(strata["estimates"].round(3).to_string(index=False)); print("p heterogeneity:", round(strata["p_heterogeneity"], 4))
