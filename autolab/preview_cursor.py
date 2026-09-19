"""Ordinary keyset pagination through sorted MCP previews; diagnostic only.

Requires a stable non-null string column and matching sort/filter order.
This enumerates distinct values, not rows, and does not infer a query predicate.
"""


async def enumerate_strings(call, handle, column, budget):
    if budget < 1:
        return {"values": [], "complete": False, "reason": "budget_exhausted", "calls": 0}
    peek = await call("sort_data", {"data_label": handle, "key_name": column, "ascending": True})
    count = 1
    values = []
    cursor = None
    previous_remaining = None
    while True:
        if not isinstance(peek, dict) or not isinstance(peek.get("handle"), str):
            raise ValueError("Expected a data handle")
        n = peek.get("num_records")
        if type(n) is not int or n < 0:
            raise ValueError("Invalid remaining row count")
        matches = [x for x in peek.get("key_details", []) if x.get("name") == column]
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous column preview")
        page = matches[0].get("first_3_values")
        if not isinstance(page, list) or len(page) != min(n, 3):
            raise ValueError("Incomplete or oversized preview")
        if any(type(v) is not str for v in page) or page != sorted(page):
            raise ValueError("Unsupported null/type or unsorted preview")
        if cursor is not None and any(v <= cursor for v in page):
            raise ValueError("Cursor did not advance")
        if previous_remaining is not None and n >= previous_remaining:
            raise ValueError("Remaining count did not decrease")
        for value in page:
            if not values or values[-1] != value:
                values.append(value)
        if n <= len(page):
            return {"values": values, "complete": True, "reason": "exhausted_sorted_relation", "calls": count}
        if count >= budget:
            return {"values": values, "complete": False, "reason": "budget_exhausted", "calls": count}
        cursor = page[-1]
        previous_remaining = n
        peek = await call("filter_data", {"data_label": peek["handle"], "key_name": column,
                                          "condition": "greater_than", "value": cursor})
        count += 1
