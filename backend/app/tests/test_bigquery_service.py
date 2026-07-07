from app.services.bigquery_service import map_to_bigquery_type, sanitize_table_name


def test_sanitize_table_name_generates_safe_prefixed_name():
    assert sanitize_table_name("Sales Data 2026", 3) == "dataset_3_sales_data_2026"
    assert sanitize_table_name(" $$$ ", 4) == "dataset_4_dataset"
    assert sanitize_table_name("A/B:C*D", 5) == "dataset_5_a_b_c_d"


def test_map_to_bigquery_type_defaults_unknown_values_to_string():
    assert map_to_bigquery_type("INTEGER") == "INT64"
    assert map_to_bigquery_type("FLOAT") == "FLOAT64"
    assert map_to_bigquery_type("BOOLEAN") == "BOOL"
    assert map_to_bigquery_type("DATE") == "DATE"
    assert map_to_bigquery_type("DATETIME") == "DATETIME"
    assert map_to_bigquery_type("STRING") == "STRING"
    assert map_to_bigquery_type("unknown") == "STRING"
