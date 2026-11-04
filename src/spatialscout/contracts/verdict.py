"""Hypothesis verdicts (revision 3, ticket 10b): the plan splits the question into sub-claims, each with the outcome
the researcher's hypothesis predicts, and a frozen rule compares that prediction with the verified claims."""

from typing import Literal

from pydantic import Field

from .base import Contract

Prediction = Literal["holds", "drops"]


class SubClaim(Contract):
    """One testable part of the question: a population, its genes, and what the hypothesis predicts under stricter
    assignment conditions. A prediction, never an outcome."""

    text: str = Field(description="The sub-claim as a question-scoped statement, for example 'podocyte LRP2/CUBN presence persists'.")
    cell_type: str = Field(description="A cell type label from the dataset's label rules.")
    genes: list[str] = Field(description="Panel genes the sub-claim is about.")
    predicted: Prediction = Field(
        description="What the researcher's hypothesis predicts: 'holds' (the signal stays when assignment is stricter, "
        "as real cell content would) or 'drops' (it falls beyond random thinning, as admixture from neighbours would)."
    )


class SubClaimVerdict(Contract):
    sub_claim: SubClaim
    verdict: Literal["confirmed", "refuted", "inconclusive"]
    reason: str
    claim_ids: list[str] = Field(description="The verified claim versions the verdict rests on.")
    dataset_id: str


class HypothesisVerdict(Contract):
    """Every sub-claim's verdict, in the investigation's sections and under the controls its claims cite."""

    question: str
    scope: str
    verdicts: list[SubClaimVerdict]
    rule: str
