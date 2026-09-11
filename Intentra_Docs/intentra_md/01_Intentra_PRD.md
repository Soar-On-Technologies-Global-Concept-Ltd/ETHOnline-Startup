**Intentra --- Product Requirements Document**

*Intentra*

Version: September 2026

# 1. Executive Summary

Intentra is an AI-native transaction assurance platform that enables
people, businesses, and eventually external AI agents to discover,
negotiate, pay for, fulfill, and resolve real-world transactions while
keeping every action tied to explicit intent and authority.

Core lifecycle: Intent → Recommendation → Choice → Authorization →
Agreement → Payment → Fulfillment → Evidence → Outcome → Resolution →
Settlement.

# 2. Product Principle

AI can act, but AI cannot create its own authority.

# 3. Problem

-   Agentic commerce is increasingly capable of discovering products,
    negotiating and initiating payments.

-   Payment completion does not prove that a real-world service was
    delivered.

-   Users and businesses need a durable record of what was requested,
    authorized, agreed, paid, delivered and resolved.

-   Disputes often require combining structured transaction data with
    natural-language messages, photos and other evidence.

# 4. Target Users

-   Consumers

-   Professionals: cleaners, painters, plumbers, electricians,
    mechanics, photographers, developers and similar providers

-   Merchants

-   SMEs and enterprise procurement teams

-   AI-agent developers, marketplaces and fintechs

# 5. Initial Wedge

Nigeria-first professional services where fulfillment is observable:
cleaning, painting, plumbing, electrical work, repairs and related
services.

# 6. Consumer Journey

1.  User describes a goal in natural language.

2.  Intentra converts the request into structured intent.

3.  AI finds providers and recommends the best option plus alternatives.

4.  AI may negotiate within the user\'s constraints.

5.  User approves or a preconfigured policy authorizes the action.

6.  Intentra records the agreement.

7.  Moove handles the payment stage.

8.  Provider fulfills the service.

9.  Intentra collects evidence and verifies the outcome.

10. Transaction is completed or enters complaint/resolution flow.

# 7. Core Features

-   AI discovery and comparison

-   Best recommendation + alternatives

-   AI communication and constrained negotiation

-   Intent engine

-   Authorization/policy engine

-   Agreement engine

-   Moove payment integration

-   Fulfillment tracking

-   Evidence layer

-   Outcome verification

-   Customer and provider complaints

-   Resolution/refund engine

-   Transaction history

-   Trust and reputation

-   Business procurement

-   External Transaction Assurance API/SDK

# 8. Authorization Modes

  -----------------------------------------------------------------------
  Mode                                Behavior
  ----------------------------------- -----------------------------------
  Manual                              AI prepares transaction; user
                                      explicitly approves.

  One-Tap                             AI handles discovery and
                                      preparation; user reviews and
                                      approves.

  Controlled Autonomy                 Predefined policy allows eligible
                                      actions; AI cannot modify the
                                      policy.
  -----------------------------------------------------------------------

# 9. Transaction State Machine

REQUESTED → MATCHED → QUOTED → SELECTED → AUTHORIZED → AGREED → PAID →
IN_PROGRESS → FULFILLMENT_SUBMITTED → VERIFICATION → COMPLETED →
SETTLED.

Exception states: CANCELLED, FAILED, REFUND_REQUESTED, PARTIAL_REFUND,
DISPUTED, ADJUDICATION, RESOLVED.

# 10. Evidence Model

-   Original intent

-   AI recommendation and alternatives

-   User selection

-   Authorization decision

-   Provider agreement

-   Payment records

-   Messages

-   Timestamps

-   Photos/documents

-   Fulfillment events

-   Completion confirmation

-   Complaints

-   Refunds

-   Resolution decisions

# 11. Outcome Engine

The outcome engine compares ORIGINAL INTENT → AUTHORIZED ACTION →
AGREEMENT → ACTUAL FULFILLMENT and classifies the result as fulfilled,
partially fulfilled, not fulfilled, or ambiguous.

# 12. Resolution

-   Level 1: deterministic rules

-   Level 2: AI-assisted analysis

-   Level 3: GenLayer adjudication for selected ambiguous cases

-   Level 4: human review

# 13. Business Procurement

Example: \'Find 30 laptops, 20 monitors and 30 chairs under ₦15m.\'
Intentra can gather suppliers, compare quotes, negotiate within policy,
create an agreement, coordinate payment, track fulfillment and resolve
exceptions.

# 14. External Agent API

The same assurance infrastructure can expose intent, authorization,
transaction, quote, payment, fulfillment, evidence, complaint, dispute
and resolution capabilities to external agents.

# 15. Non-Goals

-   Building a payment network

-   Building a foundation model

-   Building a logistics fleet

-   Creating a new generic MCP protocol

-   Making blockchain visible to users

-   Launching every marketplace category at once

# 16. Success Metrics

  -----------------------------------------------------------------------
  Metric                              Purpose
  ----------------------------------- -----------------------------------
  Verified Agentic GMV                North-star economic activity

  Completed transactions              Core utility

  Fulfillment rate                    Outcome quality

  Dispute/refund rate                 Risk signal

  Repeat transaction rate             Product-market fit

  AI-assisted transactions            Agent adoption

  AI-originated GMV                   Agentic usage

  Resolution time                     Trust and operations
  -----------------------------------------------------------------------

# 17. Long-Term Positioning

The transaction assurance layer for AI agents.

Short positioning: AI handles the transaction. You stay in control.
