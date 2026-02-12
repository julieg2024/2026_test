"""Tests for data models and layer detection."""

from data_lineage_tool.models import DataLayer, detect_layer


class TestDetectLayer:
    def test_raw_schema(self):
        assert detect_layer("raw.customers") == DataLayer.RAW

    def test_source_schema(self):
        assert detect_layer("source.events") == DataLayer.RAW

    def test_staging_schema(self):
        assert detect_layer("staging.stg_customers") == DataLayer.STAGING

    def test_stg_schema(self):
        assert detect_layer("stg.orders") == DataLayer.STAGING

    def test_mart_schema(self):
        assert detect_layer("mart.customer_orders") == DataLayer.MART

    def test_analytics_schema(self):
        assert detect_layer("analytics.revenue") == DataLayer.MART

    def test_name_prefix_raw(self):
        assert detect_layer("raw_events") == DataLayer.RAW

    def test_name_prefix_stg(self):
        assert detect_layer("stg_orders") == DataLayer.STAGING

    def test_name_prefix_dim(self):
        assert detect_layer("dim_products") == DataLayer.MART

    def test_name_prefix_fct(self):
        assert detect_layer("fct_sales") == DataLayer.MART

    def test_unknown(self):
        assert detect_layer("my_table") == DataLayer.UNKNOWN

    def test_case_insensitive(self):
        assert detect_layer("RAW.Customers") == DataLayer.RAW
        assert detect_layer("Staging.Stg_Orders") == DataLayer.STAGING
