"""Preliminary endotype clustering from baseline metabolic, genetic and treatment covariates.

Research-only and hypothesis-generating. A cluster here is a data-driven subgroup,
not a validated disease endotype. Clusters are fitted on training subjects only and
then assigned to calibration and test subjects, so labels never see held-out data.

Baseline covariates only: no CGM summary from the outcome period is used, because
low-glucose burden computed over the whole record would leak the prediction target.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .covariates import METABOLIC, GENETIC, TREATMENT, available


def _fit_kmeans(X: np.ndarray, k: int, seed: int):
    from sklearn.cluster import KMeans
    return KMeans(n_clusters=k, n_init=20, random_state=seed).fit(X)


class EndotypeClusterer:
    """Median-impute, standardise, then k-means with k chosen by silhouette and bootstrap stability."""

    def __init__(self, columns: list[str] | None = None, k_range=(2, 3, 4, 5), seed: int = 42,
                 n_boot: int = 50, min_cluster_fraction: float = 0.10, use_pca: bool = True,
                 variance_target: float = 0.80, max_components: int = 6):
        self.columns, self.k_range, self.seed = columns, tuple(k_range), seed
        self.use_pca, self.variance_target, self.max_components = use_pca, variance_target, max_components
        self.n_boot, self.min_cluster_fraction = n_boot, min_cluster_fraction

    def fit(self, cov: pd.DataFrame):
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import silhouette_score, adjusted_rand_score
        cols = self.columns or available(cov, METABOLIC + GENETIC + TREATMENT)
        cols = [c for c in cols if c in cov.columns and cov[c].notna().sum() >= 5 and cov[c].nunique() > 1]
        if len(cols) < 2 or len(cov) < 12:
            raise ValueError("Need at least 2 informative covariates and 12 training subjects to cluster")
        self.columns_ = cols
        self.imputer_ = SimpleImputer(strategy="median").fit(cov[cols])
        self.scaler_ = StandardScaler().fit(self.imputer_.transform(cov[cols]))
        X = self._project(cov, fitting=True)
        rng = np.random.default_rng(self.seed)
        table = []
        for k in self.k_range:
            if k >= len(X):
                continue
            km = _fit_kmeans(X, k, self.seed)
            sil = float(silhouette_score(X, km.labels_))
            smallest = float(np.bincount(km.labels_, minlength=k).min() / len(X))
            aris = []
            for _ in range(self.n_boot):
                idx = rng.integers(0, len(X), len(X))
                kb = _fit_kmeans(X[idx], k, int(rng.integers(1e9)))
                aris.append(adjusted_rand_score(km.labels_, kb.predict(X)))
            table.append({"k": k, "silhouette": sil, "stability_ari": float(np.mean(aris)),
                          "smallest_cluster_fraction": smallest})
        self.selection_ = pd.DataFrame(table)
        ok = self.selection_[self.selection_.smallest_cluster_fraction >= self.min_cluster_fraction]
        pick = ok if len(ok) else self.selection_
        # Rank by stability first (reproducibility), silhouette second.
        self.k_ = int(pick.sort_values(["stability_ari", "silhouette"], ascending=False).iloc[0].k)
        self.model_ = _fit_kmeans(X, self.k_, self.seed)
        best = self.selection_[self.selection_.k == self.k_].iloc[0]
        self.quality_ = {"k": self.k_, "silhouette": float(best.silhouette), "stability_ari": float(best.stability_ari),
                         "smallest_cluster_fraction": float(best.smallest_cluster_fraction),
                         "preliminary": bool(best.stability_ari < 0.8 or best.silhouette < 0.25)}
        return self

    def _project(self, cov: pd.DataFrame, fitting: bool = False) -> np.ndarray:
        X = self.scaler_.transform(self.imputer_.transform(cov[self.columns_]))
        if not self.use_pca:
            return X
        if fitting:
            from sklearn.decomposition import PCA
            full = PCA(random_state=self.seed).fit(X)
            cum = np.cumsum(full.explained_variance_ratio_)
            n = int(min(self.max_components, np.searchsorted(cum, self.variance_target) + 1, X.shape[1]))
            self.pca_ = PCA(n_components=n, random_state=self.seed).fit(X)
            self.pca_summary_ = pd.DataFrame({"component": [f"PC{i+1}" for i in range(n)],
                                              "variance_explained": self.pca_.explained_variance_ratio_.round(3)})
            self.loadings_ = pd.DataFrame(self.pca_.components_.T, index=self.columns_,
                                          columns=self.pca_summary_.component).round(2)
        return self.pca_.transform(X)

    def transform(self, cov: pd.DataFrame) -> pd.Series:
        miss = [c for c in self.columns_ if c not in cov.columns]
        if miss:
            raise ValueError(f"Missing covariates for cluster assignment: {miss}")
        X = self._project(cov)
        return pd.Series(self.model_.predict(X), index=cov.subject_id.values, name="endotype")

    def profile(self, cov: pd.DataFrame) -> pd.DataFrame:
        """Cluster means in original units, for a clinician to read and name (or reject)."""
        lab = self.transform(cov).to_numpy()
        prof = cov[self.columns_].groupby(lab).mean().round(2)
        prof.insert(0, "n_subjects", pd.Series(lab).value_counts().sort_index())
        prof.index.name = "endotype"
        return prof


def endotype_features(labels: pd.Series, k: int, subject_ids: pd.Series) -> pd.DataFrame:
    """One-hot endotype indicators (k-1 columns; cluster 0 is the reference) aligned to windows."""
    lab = subject_ids.astype(str).map(labels)
    return pd.DataFrame({f"endotype_{j}": (lab == j).astype(float).to_numpy() for j in range(1, k)},
                        index=subject_ids.index)
