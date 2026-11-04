"""SpatialScout data contracts. Pydantic models here are the single source of truth for every shape
that crosses a module or the HTTP boundary; TypeScript types are generated from them (see `schema.py`)."""

from .agent import FollowUpDecision, FollowUpProposal, FollowUpRequest, FollowUpStatus, OpenQuestion
from .assignment import AuditMetrics, SectionAudit
from .audit_log import GENESIS_HASH, AuditEntry, AuditEntryKind, ChainCheckResult
from .channels import ChannelSet, RecordedBoxes, RenderedChannel
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
    ClaimDirection,
    NeighbourPattern,
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
    AgentDecisionEvent,
    BudgetExhaustedEvent,
    ClaimDraftedEvent,
    ClaimRejectedEvent,
    ClaimVerifiedEvent,
    VerdictEvent,
    ReviewDecidedEvent,
    PlanRejectedEvent,
    ToolFailedEvent,
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
    AuditIndex,
    AuditIndexEntry,
    AuditResult,
    AuditRules,
    AuditSectionValues,
    CompositeFigure,
    ConditionEffect,
    ContrastIndex,
    ContrastIndexEntry,
    ContrastResult,
    ContrastRules,
    ContrastRunConfiguration,
    ContrastSection,
    EvidenceRegion,
    Finding,
    GateStatus,
    LeaveOneSectionOut,
    LeaveOneSectionOutVerdict,
    LeftOutSection,
    MarkerPairsSource,
    PooledConditionValue,
    Population,
    Region,
    RegionAuditRequest,
    SectionLog2Value,
)
from .controls import LabelRuleArm, LabelSensitivityCheck, RandomThinningControl
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
from .datafit import DataFit, DataGap, NeedKind, NeedMatch, PublicDataset, UploadPrefill
from .lab import (
    CoMention,
    DispatchProposal,
    LabAgent,
    LabEvent,
    LabReport,
    LabRun,
    LabTask,
    LabTaskProposal,
    LiteratureDigest,
    LiteratureRecord,
    LiteratureReview,
    LiteratureStatement,
    LiteratureStatementDraft,
    ProteinCrossCheck,
    PublicationFigure,
)
from .protein import (
    KpmpCellMap,
    KpmpChannel,
    KpmpManifest,
    KpmpParticipant,
    KpmpResultEntry,
    KpmpTile,
    ProteinAuditResult,
    ProteinConditionRow,
    ProteinThreshold,
)
from .region import (
    CellColumns,
    MoleculeColumns,
    PackedCellColumns,
    PackedColumn,
    PackedMoleculeColumns,
    PackedRegionView,
    RegionView,
    OutlineMeasures,
    StructureMask,
    StructureProposal,
    StructureRun,
    StructureSeed,
)
from .review import CheckKind, CheckResult, ClaimChallenge, ClaimChallenges, FieldChange, ReviewDecision, ReviewRequest, VerificationResult, VisualAnswer
from .verdict import HypothesisVerdict, Prediction, SubClaim, SubClaimVerdict
from .voice import Transcription

from .depth import DepthBin, DepthPoints, DepthProfile, DepthProfileRequest, DepthSource  # noqa: E402

__all__ = [name for name in dir() if not name.startswith("_")]
