from tests.conftest import last_request_params, tool_fn

RESOURCE_CASES = [
    ("recurrings", "recurring", 101),
    ("price_lists", "price_list", 102),
    ("warehouses", "warehouse", 103),
    ("warehouse_documents", "warehouse_document", 104),
    ("categories", "category", 105),
    ("departments", "department", 106),
    ("issuers", "issuer", 107),
    ("bank_accounts", "bank_account", 108),
    ("webhooks", "webhook", 109),
]


async def test_generic_read_only_list_and_get_tools() -> None:
    for plural, singular, record_id in RESOURCE_CASES:
        listed = await tool_fn(f"list_{plural}")(page=2, per_page=1)
        fetched = await tool_fn(f"get_{singular}")(**{f"{singular}_id": record_id})

        assert listed["page"] == 2
        assert listed["has_more"] is True
        assert listed[plural][0]["id"] == record_id
        assert "token" not in listed[plural][0]
        if plural == "bank_accounts":
            assert listed[plural][0]["currency"] == "PLN"
        assert fetched["id"] == record_id
        assert "token" not in fetched
        assert last_request_params(f"/{plural}.json") == {"page": "2", "per_page": "1"}


async def test_list_warehouse_actions_forwards_all_supported_filters() -> None:
    result = await tool_fn("list_warehouse_actions")(
        warehouse_id=103,
        kind="income",
        product_id=9,
        date_from="2026-09-01",
        date_to="2026-09-30",
        from_warehouse_document=1,
        to_warehouse_document=2,
        warehouse_document_id=104,
        page=3,
        per_page=1,
    )

    assert result["page"] == 3
    assert result["has_more"] is True
    assert result["warehouse_actions"][0]["kind"] == "income"
    assert result["warehouse_actions"][0]["quantity"] == "5.0"
    assert result["warehouse_actions"][0]["warehouse_document_id"] == 104
    assert result["warehouse_actions"][0]["date"] == "2026-09-15"
    assert last_request_params("/warehouse_actions.json") == {
        "warehouse_id": "103",
        "kind": "income",
        "product_id": "9",
        "date_from": "2026-09-01",
        "date_to": "2026-09-30",
        "from_warehouse_document": "1",
        "to_warehouse_document": "2",
        "warehouse_document_id": "104",
        "page": "3",
        "per_page": "1",
    }
