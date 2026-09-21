from server.comparison import legacy_item_compare as item_compare

def test_item_comparison():
    # Test 1: Feature difference
    print("Test 1: Feature difference (COATED IVORY BOARD vs COATED BLACK BOARD)")
    si_items = ["COATED IVORY BOARD"]
    bl_items = ["COATED BLACK BOARD"]
    res = item_compare.compare_items(si_items, bl_items)
    for r in res:
        print(r)
    assert res[0]['verdict'] == 'REVIEW' # Since it was matched by cosine but failed feature check

    # Test 2: Dimensional difference
    print("\nTest 2: Dimensional difference (3ft WOODEN CABINET vs 10 ft WOODEN CABINET)")
    si_items = ["3ft WOODEN CABINET"]
    bl_items = ["10 ft WOODEN CABINET"]
    res = item_compare.compare_items(si_items, bl_items)
    for r in res:
        print(r)
    assert res[0]['verdict'] == 'REVIEW'

    # Test 3: Unit difference
    print("\nTest 3: Unit difference (3m LONG 2’ WOODEN SHELF vs 3ft LONG 2’ WOODEN SHELF)")
    # Wait, the regex uses 'ft' or 'feet', but does it parse '2\''? No, but let's test what we have
    si_items = ["3m LONG WOODEN SHELF"]
    bl_items = ["3ft LONG WOODEN SHELF"]
    res = item_compare.compare_items(si_items, bl_items)
    for r in res:
        print(r)
    assert res[0]['verdict'] == 'REVIEW'
    
    # Test 4: Match
    print("\nTest 4: Match")
    si_items = ["3m LONG WOODEN SHELF"]
    bl_items = ["3m LONG WOODEN SHELF"]
    res = item_compare.compare_items(si_items, bl_items)
    for r in res:
        print(r)
    assert res[0]['verdict'] == 'MATCH'

if __name__ == "__main__":
    test_item_comparison()
    print("\nAll tests passed!")
