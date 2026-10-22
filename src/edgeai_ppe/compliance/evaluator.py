from edgeai_ppe.constants import CLASS_STATUS

def evaluate_status(class_name: str) -> str:
    """Map a class to status; this does not decide person-level compliance."""
    try:
        return CLASS_STATUS[class_name]
    except KeyError as exc:
        raise ValueError(f"Unknown PPE class: {class_name}") from exc

# TODO: person association, temporal rules and duplicate suppression.
# Absence of helmet/vest alone must not be converted into a violation here.
