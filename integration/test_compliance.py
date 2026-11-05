
from ppe_compliance import evaluate_detection

TEST_CLASSES = [
    (0, "helmet", "compliant"),
    (1, "no_helmet", "violation"),
    (2, "person", "detected"),
    (3, "safety_vest", "compliant"),
    (4, "no_safety_vest", "violation"),
]

for class_id, name, expected_status in TEST_CLASSES:
    detection = {
        "class_id": class_id,
        "class_name": name,
        "confidence": 0.85,
        "bbox": [10, 20, 100, 200]
    }

    result = evaluate_detection(
        detection, width=640, height=480
    )

    assert result["status"] == expected_status

    print(f"PASS: {name} -> {expected_status}")


# Invalid input test
invalid_detection = {
    "class_id": 99,
    "class_name": "unknown",
    "confidence": 0.85,
    "bbox": [10, 20, 100, 200]
}

try:
    evaluate_detection(invalid_detection, 640, 480)
    raise AssertionError("Invalid class was accepted")
except ValueError:
    print("PASS: Invalid class rejected")

print("\nALL COMPLIANCE TESTS PASSED")
