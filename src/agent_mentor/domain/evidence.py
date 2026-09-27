from enum import StrEnum


class EvidenceGatePolicy(StrEnum):
    CURRENT_BINARY_V1 = "current_binary_v1"
    CLAUSE_DEMAND_V1 = "clause_demand_v1"
