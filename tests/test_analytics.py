"""
Unit tests for Block 6 analytics modules.

All tests use mock DataFrames — no live database connection required.
"""

import importlib.util

import numpy as np
import pandas as pd
import pytest

_HAS_LIFETIMES = importlib.util.find_spec("lifetimes") is not None

# ──────────────────────────────────────────────────────────────
# Fixture factories
# ──────────────────────────────────────────────────────────────


def make_funnel_df() -> pd.DataFrame:
    """Minimal funnel data for CustomerJourneyAnalyzer tests."""
    stage_data = [
        ("registered", 1),
        ("registered", 1),
        ("registered", 1),
        ("activated", 2),
        ("activated", 2),
        ("matched", 3),
        ("converted", 4),
        ("retained", 5),
    ]
    rows = []
    for i, (stage, num) in enumerate(stage_data):
        rows.append(
            {
                "empresa_id": f"e{i}",
                "segmento": "moda" if i % 2 == 0 else "uniformes",
                "porte": "medio",
                "estado": "SC",
                "current_stage": stage,
                "stage_num": num,
                "dias_signup_para_ativacao": 5 + i,
                "dias_ativacao_para_match": (3 + i) if num >= 3 else None,
                "dias_match_para_conversao": (10 + i) if num >= 4 else None,
                "dias_conversao_para_retencao": (20 + i) if num >= 5 else None,
                "cohort_mes": pd.Timestamp("2024-01-01"),
                "total_pedidos": max(0, num - 1),
                "gmv_total": float(num * 1000),
            }
        )
    return pd.DataFrame(rows)


def make_cohort_df() -> pd.DataFrame:
    """Sample cohort data with 3 cohorts × 6 months (each cohort has a different decay rate)."""
    rows = []
    cohorts = pd.date_range("2024-01-01", periods=3, freq="MS")
    # Different decay rates per cohort so best != worst
    decay_rates = [2, 4, 6]  # n_ativos = max(1, 20 - mes_n * decay)
    for cohort, decay in zip(cohorts, decay_rates):
        for mes_n in range(6):
            n_ativos = max(1, 20 - mes_n * decay)
            rows.append(
                {
                    "cohort_mes": cohort,
                    "cohort_label": cohort.strftime("%Y-%m"),
                    "cohort_size": 20,
                    "mes_n": mes_n,
                    "n_ativos": n_ativos,
                    "retention_rate_pct": round(n_ativos / 20 * 100, 1),
                    "receita_cohort": float(n_ativos * 500),
                }
            )
    return pd.DataFrame(rows)


def make_performance_df() -> pd.DataFrame:
    """Sample int_oficina_performance for OficinaScorer tests."""
    rows = []
    for i in range(1, 8):
        n_aval = i * 2
        rows.append(
            {
                "oficina_id": f"o{i}",
                "nome_fantasia": f"Oficina {i}",
                "estado": "SC",
                "cidade": "Blumenau",
                "tier": "premium" if i % 3 == 0 else "standard",
                "capacidade_mensal_pecas": 500 + i * 100,
                "total_pedidos": 10 + i * 5,
                "pedidos_finalizados": 8 + i * 4,
                "total_avaliacoes": n_aval,
                "nota_qualidade_media": 3.5 + i * 0.1 if n_aval >= 3 else None,
                "nota_pontualidade_media": 3.2 + i * 0.1 if n_aval >= 3 else None,
                "nota_comunicacao_media": 3.8 + i * 0.05 if n_aval >= 3 else None,
                "score_qualidade_media": 3.5 + i * 0.1,
                "score_pontualidade_media": 3.2 + i * 0.1,
                "score_comunicacao_media": 3.8 + i * 0.05,
                "win_rate_pct": 40.0 + i * 5,
                "taxa_aprovacao_media_pct": 85.0 + i,
                "pct_entrega_no_prazo": 80.0 + i * 2,
                "tempo_medio_resposta_h": max(0.5, 12 - i),
                "total_certificacoes": i % 4,
                "score_certificacoes": float(i % 4),
                "tem_abvtex": i % 3 == 0,
                "tem_cert_premium": i % 5 == 0,
                "ativo_recente": True,
            }
        )
    return pd.DataFrame(rows)


def make_pedidos_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "pedido_id": f"p{i}",
                "empresa_id": f"e{i}",
                "categoria_id": f"cat{i % 3}",
                "quantidade_total": 100 + i * 50,
                "valor_estimado": 5000.0 + i * 1000,
                "estado_preferencia": "SC",
                "empresa_estado": "SC",
                "empresa_segmento": "moda",
                "empresa_porte": "medio",
            }
            for i in range(1, 5)
        ]
    )


def make_oficinas_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "oficina_id": f"o{i}",
                "estado": "SC" if i <= 3 else "SP",
                "cidade": "Blumenau",
                "capacidade_mensal_pecas": 300 + i * 100,
                "score_medio": 7.0 + i * 0.3,
                "score_qualidade": 3.0 + i * 0.2,
                "score_pontualidade": 3.0 + i * 0.15,
                "win_rate_pct": 40.0 + i * 5,
                "pct_entrega_no_prazo": 80.0 + i * 2,
                "tempo_medio_resposta_h": max(1.0, 10.0 - i),
                "tem_abvtex": i % 2 == 0,
                "tem_cert_premium": i % 4 == 0,
                "tier": "premium" if i % 2 == 0 else "standard",
            }
            for i in range(1, 6)
        ]
    )


# ──────────────────────────────────────────────────────────────
# CustomerJourneyAnalyzer tests
# ──────────────────────────────────────────────────────────────


class TestCustomerJourneyAnalyzer:
    @pytest.fixture
    def analyzer(self):
        from src.analytics.customer_journey import CustomerJourneyAnalyzer

        return CustomerJourneyAnalyzer(engine=None)  # engine unused when df is passed

    def test_get_funnel_summary_shape(self, analyzer):
        df = make_funnel_df()
        # Patch engine so _load_funnel_data is never called
        result = analyzer.get_funnel_summary(df=df)
        assert len(result) == 5  # 5 stages
        assert set(result.columns) >= {"stage", "count", "pct_of_top"}

    def test_funnel_counts_are_monotone(self, analyzer):
        df = make_funnel_df()
        result = analyzer.get_funnel_summary(df=df)
        counts = result["count"].tolist()
        assert counts == sorted(counts, reverse=True), "Funnel counts must be non-increasing"

    def test_top_stage_pct_is_100(self, analyzer):
        df = make_funnel_df()
        result = analyzer.get_funnel_summary(df=df)
        assert result.iloc[0]["pct_of_top"] == 100.0

    def test_get_time_to_convert_columns(self, analyzer):
        df = make_funnel_df()
        result = analyzer.get_time_to_convert(df=df)
        assert "transicao" in result.columns
        assert "mediana_dias" in result.columns
        assert len(result) == 4  # 4 transitions

    def test_get_drop_off_analysis_sorted(self, analyzer):
        df = make_funnel_df()
        result = analyzer.get_drop_off_analysis(df=df)
        drops = result["drop_pct"].tolist()
        assert drops == sorted(drops, reverse=True)

    def test_get_funnel_by_segment(self, analyzer):
        df = make_funnel_df()
        result = analyzer.get_funnel_by_segment(df=df)
        assert "segmento" in result.columns
        assert "pct_of_segment" in result.columns
        # Should have entries for each segment × stage
        assert len(result) == len(result["segmento"].unique()) * 5

    def test_get_cohort_funnel(self, analyzer):
        df = make_funnel_df()
        result = analyzer.get_cohort_funnel(df=df)
        assert "cohort_mes" in result.columns
        assert "n_empresas" in result.columns
        assert "pct_registered" in result.columns


# ──────────────────────────────────────────────────────────────
# CohortAnalyzer tests
# ──────────────────────────────────────────────────────────────


class TestCohortAnalyzer:
    @pytest.fixture
    def analyzer(self):
        from src.analytics.cohort_analysis import CohortAnalyzer

        return CohortAnalyzer(engine=None)

    def test_retention_matrix_shape(self, analyzer):
        df = make_cohort_df()
        matrix = analyzer.build_retention_matrix(df=df)
        assert matrix.shape == (3, 6)  # 3 cohorts × 6 month columns
        assert matrix.index.name == "Coorte"

    def test_retention_matrix_m0_is_100(self, analyzer):
        df = make_cohort_df()
        matrix = analyzer.build_retention_matrix(df=df)
        # Month 0 (mes_n=0) retention should be 100% for all cohorts
        assert (matrix[0] == 100.0).all()

    def test_revenue_matrix_no_negatives(self, analyzer):
        df = make_cohort_df()
        matrix = analyzer.build_revenue_matrix(df=df)
        assert (matrix >= 0).all().all()

    def test_avg_retention_curve_length(self, analyzer):
        df = make_cohort_df()
        curve = analyzer.get_average_retention_curve(df=df)
        assert len(curve) == 6  # 0..5 months

    def test_cohort_summary_columns(self, analyzer):
        df = make_cohort_df()
        summary = analyzer.get_cohort_summary(df=df)
        expected = {"cohort", "cohort_size", "retention_m0", "retention_m1", "receita_total"}
        assert expected.issubset(set(summary.columns))

    def test_ltv_by_cohort_horizon(self, analyzer):
        df = make_cohort_df()
        ltv = analyzer.get_ltv_by_cohort(df=df, horizon_months=3)
        assert len(ltv) == 3
        assert "ltv_per_empresa" in ltv.columns
        assert (ltv["ltv_per_empresa"] > 0).all()

    def test_best_worst_cohorts(self, analyzer):
        df = make_cohort_df()
        result = analyzer.get_best_and_worst_cohorts(df=df, metric="retention_m3")
        assert result["best"] is not None
        assert result["worst"] is not None
        assert result["best"] != result["worst"]


# ──────────────────────────────────────────────────────────────
# OficinaScorer tests
# ──────────────────────────────────────────────────────────────


class TestOficinaScorer:
    @pytest.fixture
    def scorer(self):
        from src.analytics.scoring_model import OficinaScorer

        return OficinaScorer(engine=None)

    def test_compute_scores_columns(self, scorer):
        df = make_performance_df()
        result = scorer.compute_scores(df=df)
        expected_cols = {
            "oficina_id", "score_composto", "ranking_tier",
            "percentil_rank", "score_qualidade",
        }
        assert expected_cols.issubset(set(result.columns))

    def test_scores_in_valid_range(self, scorer):
        df = make_performance_df()
        result = scorer.compute_scores(df=df)
        assert result["score_composto"].between(0, 10).all(), "Scores must be in [0, 10]"

    def test_scores_sorted_descending(self, scorer):
        df = make_performance_df()
        result = scorer.compute_scores(df=df)
        scores = result["score_composto"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_ranking_tier_values(self, scorer):
        df = make_performance_df()
        result = scorer.compute_scores(df=df)
        valid_tiers = {"elite", "premium", "standard", "basico"}
        assert set(result["ranking_tier"]).issubset(valid_tiers)

    def test_explain_score_structure(self, scorer):
        df = make_performance_df()
        result = scorer.explain_score("o3", df=df)
        assert "score_composto" in result
        assert "dimensions" in result
        dims = result["dimensions"]
        assert set(dims.keys()) == {
            "qualidade", "pontualidade", "comunicacao",
            "experiencia", "certificacoes", "velocidade",
        }
        # Contributions must sum to composite score (within rounding)
        total_contrib = sum(v["contribution"] for v in dims.values())
        assert abs(total_contrib - result["score_composto"]) < 0.1

    def test_explain_score_unknown_id(self, scorer):
        df = make_performance_df()
        with pytest.raises(ValueError, match="not found"):
            scorer.explain_score("nonexistent-id", df=df)

    def test_custom_weights(self, scorer):
        from src.analytics.scoring_model import ScoringWeights

        # Quality-heavy config
        w = ScoringWeights(
            qualidade=0.60, pontualidade=0.15, comunicacao=0.10,
            experiencia=0.05, certificacoes=0.05, velocidade=0.05,
        )
        from src.analytics.scoring_model import OficinaScorer as OS
        scorer2 = OS(engine=None, weights=w)
        df = make_performance_df()
        result = scorer2.compute_scores(df=df)
        assert result["score_composto"].between(0, 10).all()

    def test_invalid_weights_raise(self):
        from src.analytics.scoring_model import ScoringWeights

        with pytest.raises(ValueError, match="sum to 1.0"):
            ScoringWeights(qualidade=0.5, pontualidade=0.5, comunicacao=0.5,
                           experiencia=0.1, certificacoes=0.1, velocidade=0.1)

    def test_get_ranked_oficinas_by_estado(self, scorer):
        df = make_performance_df()
        result = scorer.get_ranked_oficinas(estado="SC", df=df)
        assert (result["estado"] == "SC").all()

    def test_tier_distribution_sums_to_total(self, scorer):
        df = make_performance_df()
        dist = scorer.get_tier_distribution(df=df)
        assert dist["n_oficinas"].sum() == len(df)


# ──────────────────────────────────────────────────────────────
# MatchOptimizer tests
# ──────────────────────────────────────────────────────────────


class TestMatchOptimizer:
    @pytest.fixture
    def optimizer(self):
        from src.analytics.match_optimization import MatchOptimizer

        return MatchOptimizer(engine=None)

    def test_compatibility_matrix_shape(self, optimizer):
        pedidos = make_pedidos_df()
        oficinas = make_oficinas_df()
        matrix = optimizer.build_compatibility_matrix(pedidos=pedidos, oficinas=oficinas)
        assert len(matrix) == len(pedidos) * len(oficinas)

    def test_scores_in_zero_one(self, optimizer):
        pedidos = make_pedidos_df()
        oficinas = make_oficinas_df()
        matrix = optimizer.build_compatibility_matrix(pedidos=pedidos, oficinas=oficinas)
        assert matrix["score"].between(0, 1).all()

    def test_get_recommendations_top_n(self, optimizer):
        pedidos = make_pedidos_df()
        oficinas = make_oficinas_df()
        matrix = optimizer.build_compatibility_matrix(pedidos=pedidos, oficinas=oficinas)
        recs = optimizer.get_recommendations(top_n=3, compat_matrix=matrix)
        for _, group in recs.groupby("pedido_id"):
            assert len(group) <= 3

    def test_get_recommendations_sorted(self, optimizer):
        pedidos = make_pedidos_df()
        oficinas = make_oficinas_df()
        matrix = optimizer.build_compatibility_matrix(pedidos=pedidos, oficinas=oficinas)
        recs = optimizer.get_recommendations(pedido_id="p1", top_n=5, compat_matrix=matrix)
        scores = recs["score"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_optimize_matching_one_per_pedido(self, optimizer):
        pedidos = make_pedidos_df()
        oficinas = make_oficinas_df()
        matrix = optimizer.build_compatibility_matrix(pedidos=pedidos, oficinas=oficinas)
        result = optimizer.optimize_matching(compat_matrix=matrix)
        # Each pedido should appear at most once
        assert result["pedido_id"].nunique() == len(result)

    def test_optimize_matching_valid_oficinas(self, optimizer):
        pedidos = make_pedidos_df()
        oficinas = make_oficinas_df()
        matrix = optimizer.build_compatibility_matrix(pedidos=pedidos, oficinas=oficinas)
        result = optimizer.optimize_matching(compat_matrix=matrix)
        valid_oids = set(oficinas["oficina_id"])
        for oid in result["oficina_id_optimal"]:
            assert oid in valid_oids

    def test_geo_score_same_state(self, optimizer):
        assert optimizer._geo_score("SC", "SC") == 1.0

    def test_geo_score_same_region(self, optimizer):
        score = optimizer._geo_score("SC", "PR")  # Both sul
        assert score == 0.8

    def test_geo_score_different_region(self, optimizer):
        score = optimizer._geo_score("SC", "CE")
        assert score == 0.5

    def test_capacity_score_sweet_spot(self, optimizer):
        # 300 / 500 = 0.6, sweet spot
        assert optimizer._capacity_score(300, 500) == 1.0

    def test_capacity_score_over_capacity(self, optimizer):
        assert optimizer._capacity_score(600, 500) < 0.5

    def test_capacity_score_zero_capacity(self, optimizer):
        assert optimizer._capacity_score(100, 0) == 0.0

    def test_empty_pedidos_returns_empty_df(self, optimizer):
        result = optimizer.build_compatibility_matrix(
            pedidos=pd.DataFrame(), oficinas=make_oficinas_df()
        )
        assert result.empty

    def test_empty_oficinas_returns_empty_df(self, optimizer):
        result = optimizer.build_compatibility_matrix(
            pedidos=make_pedidos_df(), oficinas=pd.DataFrame()
        )
        assert result.empty


# ──────────────────────────────────────────────────────────────
# CLVModel tests (no live DB, uses mock RFM DataFrame)
# ──────────────────────────────────────────────────────────────


def make_rfm_df() -> pd.DataFrame:
    """
    Minimal RFM summary for CLVModel tests.

    BG/NBD constraints:
        - recency must be 0 when frequency == 0
        - T >= recency >= 0
    """
    np.random.seed(42)
    n = 30
    # Ensure at least 1 purchase per customer so recency constraints are valid
    freq = np.random.randint(1, 8, n).astype(float)
    rec = np.random.randint(0, 300, n).astype(float)
    T = rec + np.random.randint(10, 120, n).astype(float)
    mon = np.random.uniform(500, 5000, n)
    return pd.DataFrame(
        {"frequency": freq, "recency": rec, "T": T, "monetary_value": mon},
        index=[f"e{i}" for i in range(n)],
    )


class TestCLVModel:
    @pytest.fixture
    def model(self):
        from src.analytics.clv_model import CLVModel

        return CLVModel(engine=None)

    def test_is_fitted_false_before_fit(self, model):
        assert model.is_fitted is False

    @pytest.mark.skipif(
        not _HAS_LIFETIMES,
        reason="lifetimes not installed",
    )
    def test_fit_sets_models(self, model):
        rfm = make_rfm_df()
        model.fit(df=rfm)
        assert model.is_fitted

    @pytest.mark.skipif(
        not _HAS_LIFETIMES,
        reason="lifetimes not installed",
    )
    def test_predict_clv_returns_dataframe(self, model):
        rfm = make_rfm_df()
        model.fit(df=rfm)
        result = model.predict_clv(months=12, rfm_df=rfm)
        assert isinstance(result, pd.DataFrame)
        assert "clv_12m_predicted" in result.columns
        assert len(result) == len(rfm)

    @pytest.mark.skipif(
        not _HAS_LIFETIMES,
        reason="lifetimes not installed",
    )
    def test_predict_clv_sorted_descending(self, model):
        rfm = make_rfm_df()
        model.fit(df=rfm)
        result = model.predict_clv(months=12, rfm_df=rfm)
        values = result["clv_12m_predicted"].tolist()
        assert values == sorted(values, reverse=True)

    @pytest.mark.skipif(
        not _HAS_LIFETIMES,
        reason="lifetimes not installed",
    )
    def test_prob_alive_in_zero_one(self, model):
        rfm = make_rfm_df()
        model.fit(df=rfm)
        probs = model.probability_alive(rfm_df=rfm)
        assert (probs >= 0).all() and (probs <= 1).all()

    def test_predict_raises_if_not_fitted(self, model):
        with pytest.raises(RuntimeError, match="not fitted"):
            model.predict_clv()
