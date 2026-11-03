"""SpatialScout data contracts. Pydantic models here are the single source of truth for every shape
that crosses a module or the HTTP boundary; TypeScript types are generated from them (see `schema.py`)."""

from .assignment import AuditMetrics, SectionAudit
from .audit_log import GENESIS_HASH, AuditEntry, AuditEntryKind, ChainCheckResult
from .base import (
    SCHEMA_VERSION,
    ConditionName,
    Contract,
    Contrast,
    EvidenceStatus,
    FindingKind,
    RunMode,
    canonical_json,
    checksum,
    content_id,
    new_id,
    sha256_hex,
)
from .claim import (
    CLAIM_SCHEMA_VERSION,
    CitedNumber,
    Claim,
    ClaimControls,
    ClaimDraft,
    FindingRef,
    InjectedError,
    InjectedErrorKind,
    ReviewStatus,
    VerificationStatus,
)
from .dataset import (
    CapabilityCheck,
    CapabilityReport,
    ContrastEligibility,
    DatasetFilters,
    DatasetManifest,
    FileChecksum,
    LabelCounts,
    LabelRule,
    LabelRuleSet,
    SectionInfo,
    SectionValidation,
)
from .events import (
    ClaimDraftedEvent,
    ErrorEvent,
    EventBase,
    InvestigationEvent,
    ModelCallEvent,
    PackageReadyEvent,
    PlanApprovedEvent,
    PlanProposedEvent,
    ToolFinishedEvent,
    ToolStartedEvent,
)
from .finding import (
    AuditConditionValue,
    AuditResult,
    AuditSectionValues,
    ConditionEffect,
    ContrastResult,
    EvidenceRegion,
    Finding,
    LeaveOneSectionOut,
    Population,
    Region,
    SectionLog2Value,
)
from .investigation import (
    TERMINAL_STATUSES,
    InvestigationSnapshot,
    InvestigationState,
    InvestigationStatus,
    ModeInfo,
    StartInvestigationRequest,
)
from .model_call import (
    CacheInput,
    ChatMessage,
    ModelApi,
    ModelCallRecord,
    ModelRequest,
    ModelResponse,
    Provider,
    RecordedCall,
    Recording,
    ReplayInfo,
    TokenUsage,
)
from .package import PackageInfo, PackageManifest
from .plan import Budget, Plan, PlanProposal, PlanStep, ProposedStep, ToolSpec
from .region import (
    CellColumns,
    MoleculeColumns,
    PackedCellColumns,
    PackedColumn,
    PackedMoleculeColumns,
    PackedRegionView,
    RegionView,
    StructureMask,
)
from .review import CheckResult, ReviewDecision, VerificationResult

__all__ = [name for name in dir() if not name.startswith("_")]
