**INTENTRA**

**ETHOnline 2026 Team Strategy & Partner Integration Brief**

Internal team document \| September 2026

# 1. Executive Summary

Intentra is a transaction-assurance platform for AI agents. Its core
principle is: AI can act, but AI cannot create its own authority.
Intentra connects user intent, authorization, agreement, payment,
fulfillment, evidence, outcome and resolution.

For ETHOnline, the objective is not to integrate every sponsor. We
should build one coherent transaction and use sponsor technologies only
where they strengthen a specific part of the assurance stack.

# 2. Core Product Thesis

**Intent → Recommendation → Choice → Authorization → Agreement → Payment
→ Fulfillment → Evidence → Outcome → Resolution → Settlement**

Recommendation is not authorization. The AI can discover providers and
negotiate within constraints, but it must not silently gain unrestricted
authority over the user\'s money.

# 3. Partner Opportunity Map

  -------------------------------------------------------------------------
  Partner           Prize Pool        Fit               Best Use in
                                                        Intentra
  ----------------- ----------------- ----------------- -------------------
  The Graph         \$15k             ★★★★★             Onchain evidence,
                                                        agent/transaction
                                                        history

  Hedera            \$15k             ★★★★★             Agentic payments /
                                                        x402 assurance API

  Arc / Circle      \$10k             ★★★★★             Stablecoin-native
                                                        agentic payments

  World             \$7k              ★★★★★             Human-backed agent
                                                        identity

  1inch             \$7k              ★★                Asset conversion /
                                                        DeFi, only if
                                                        necessary

  ENS               \$5k              ★★★★              Agent identity,
                                                        namespaces,
                                                        permissions

  Uniswap           \$5k              ★★★               Asset/stablecoin
  Foundation                                            conversion


                                                        and human approval

  Privy             \$5k              ★★★★★             Wallet policies,
                                                        permissions,
                                                        delegated authority

  Chainlink         \$3k              ★★★★★             Confidential
                                                        policy/risk
                                                        workflows

  Bazantic          \$3k              ★★★★★             Expose Intentra
                                                        assurance to
                                                        external agents
  -------------------------------------------------------------------------

# 4. Recommended Architecture

Human / User

↓

Identity / Human-backed agent context

↓

AI Agent

↓

INTENTRA: Intent • Policy • Authorization • Agreement • Evidence •
Outcome • Resolution

↓

Payment / Settlement Layer

↓

Fulfillment → Evidence → Outcome → Resolution

# 5. Recommended Sponsor Roles

-   **Privy:** Primary authorization layer. Enforce wallet-level
    policies, permissions, delegated access and transaction controls.


    confirmation before high-risk irreversible actions.

-   **World:** Human-backed agent identity where the selected ETHOnline
    track permits it.

-   **The Graph:** Structured onchain evidence for reputation, identity
    and transaction history.

-   **Bazantic:** Agent-facing interface for the Transaction Assurance
    API.

-   **Moove:** Payment/settlement layer. Position it as: "Moove moves
    the money; Intentra makes the transaction accountable."

-   **Hedera or Arc:** Optional hackathon-specific payment rail. Pick
    one if it becomes central; do not add both without a clear reason.

# 6. Proposed Demo

**1.** User: "Find me a verified photographer for my event, maximum
\$150."

**2.** Intentra converts the request into structured intent and spending
policy.

**3.** The agent finds providers and returns the best recommendation
plus at least two alternatives.

**4.** The agent negotiates only within the user\'s constraints.

**5.** Trust/evidence data is retrieved where useful.

**6.** The user explicitly approves the selected transaction, or a
preconfigured policy permits it.

**7.** Payment is executed through the selected payment layer.

**8.** The provider fulfills the job and submits evidence.

**9.** Intentra evaluates the outcome and records the transaction.

**10.** Failure can enter the resolution/dispute workflow.

# 7. Moove Integration Boundary

Moove should be treated as the payment/settlement layer, not as
Intentra\'s escrow or dispute engine. The current documented Moove API
centers on Receive Agent/payment links. The implementation should not
claim escrow, arbitrary recipient payouts or webhooks unless the live
documentation changes.

Intentra owns the transaction state and accountability layer: intent,
authorization, agreement, evidence, outcome and resolution.

# 8. What We Should Not Do

-   Do not integrate sponsors merely to increase the sponsor count.

-   Do not give the AI unrestricted authority over user funds.

-   Do not build separate architectures for marketplace, B2B and API.
    They share one assurance core.

-   Do not expose blockchain complexity to users unless it provides a
    concrete benefit.

-   Do not make 1inch or Uniswap central unless asset conversion is
    genuinely required.

-   Do not ignore ETHGlobal eligibility rules because Intentra existed
    before ETHOnline.

# 9. ETHOnline Eligibility Risk

Intentra already has substantial pre-event product work. ETHGlobal Start
Fresh generally requires project-specific work to begin after the event
starts, while Continuity permits extending an existing project with
event work and requires the prior work to be documented. We must select
only tracks whose eligibility matches our actual development history.

Record before submission: what existed before ETHOnline, what was built
during ETHOnline, which sponsor integrations are new, and which parts of
the demo depend on the new work.

# 10. Build Priority

  -----------------------------------------------------------------------
  Priority                Workstream              Target
  ----------------------- ----------------------- -----------------------
  P0                      Transaction core        Intent → policy →
                                                  authorization →
                                                  agreement → payment →
                                                  evidence → outcome

  P0                      Security                Privy
                                                  technically enforced
                                                  control

  P1                      Evidence                The Graph for
                                                  meaningful onchain
                                                  verification

  P1                      Identity                World if eligible and
                                                  useful

  P1                      Payment                 Moove or one
                                                  hackathon-specific rail

  P2                      External agent API      Bazantic / x402-style
                                                  assurance endpoint

  P2                      Privacy                 Chainlink confidential
                                                  workflow if time
                                                  remains
  -----------------------------------------------------------------------

# 11. Team Workstreams

**Product / UX:** Intent, provider discovery, recommendation, approval,
history and disputes.

**Backend / Protocol:** Intent schema, policy engine, authorization
state machine, transaction lifecycle, evidence and outcome.

**AI / Agents:** Discovery, ranking, constrained negotiation, tool
calling and external-agent integration.

**Blockchain / Integrations:** Privy, Graph, World and payment
integrations.

**Security:** Secrets, permissions, authorization boundaries, replay
protection and audit logs.

**Demo / Submission:** End-to-end demo, README, architecture, video,
sponsor requirements and track compliance.

# 12. Definition of Success

-   A natural-language request becomes a structured transaction intent.

-   The AI recommends and negotiates without silently expanding
    authority.

-   At least one authorization/security control is enforced technically.

-   A real payment or payment request is demonstrated end-to-end.

-   Fulfillment and evidence are part of the transaction record.

-   The system produces a clear assurance result and handles
    failure/dispute paths.

-   At least one sponsor integration is central enough that removing it
    materially weakens the product.

-   The story fits into a short demo instead of becoming a collection of
    disconnected integrations.

# 13. Team Decision

**Recommended narrative:** Intentra is the authorization and assurance
layer that lets AI agents transact in the real world without giving AI
unrestricted authority.

Select one primary sponsor stack, one payment path and one concrete
service transaction. Everything else should support that story rather
than distract from it.

# 14. References

-   ETHOnline 2026: https://ethglobal.com/events/ethonline2026

-   Moove Docs: https://docs.moove.xyz/get-started/overview

-   Moove API: https://docs.moove.xyz/api-reference/overview

*Internal working document. Verify live sponsor rules and API
capabilities immediately before submission.*
