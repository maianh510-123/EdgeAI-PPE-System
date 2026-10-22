from types import MappingProxyType

PPE_CLASSES = ("person", "helmet", "safety_vest", "no_helmet", "no_safety_vest")
CLASS_STATUS = MappingProxyType({
    "person": "detected",
    "helmet": "compliant",
    "safety_vest": "compliant",
    "no_helmet": "violation",
    "no_safety_vest": "violation",
})
