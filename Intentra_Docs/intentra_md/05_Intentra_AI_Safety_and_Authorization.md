**Intentra --- AI Safety & Authorization Specification**

*Intentra*

Version: September 2026

# 1. Core Principle

AI can propose and execute actions within authority, but it cannot
create authority.

# 2. Separation of Concerns

  -----------------------------------------------------------------------
  AI Layer                            Control Layer
  ----------------------------------- -----------------------------------
  Understand request                  Validate intent schema

  Recommend providers                 Apply eligibility rules

  Negotiate                           Enforce budget/scope

  Prepare payment                     Validate authorization

  Interpret evidence                  Apply resolution policy

  Communicate                         Record audit event
  -----------------------------------------------------------------------

# 3. Authorization Modes

-   Manual approval

-   One-tap approval

-   Controlled autonomy

# 4. Policy Example

Cleaning services: maximum ₦30,000 per transaction; verified providers
only; Lagos only; maximum 3 transactions per week; anything outside
policy requires approval.

# 5. ALLOW / ASK / BLOCK

  -----------------------------------------------------------------------
  Decision                            Meaning
  ----------------------------------- -----------------------------------
  ALLOW                               Action is within valid authority.

  ASK                                 Action may be legitimate but needs
                                      explicit approval.

  BLOCK                               Action violates policy or safety
                                      constraints.
  -----------------------------------------------------------------------

# 6. Prompt Injection

-   Treat provider messages and external web content as untrusted data.

-   Never allow content to override system policy.

-   Separate instructions from evidence.

-   Validate tool arguments against deterministic schemas.

-   Require authorization checks immediately before high-impact actions.

# 7. Financial Safety

-   No self-expanding budgets

-   No hidden fees

-   No unauthorized currency conversion

-   No provider substitution after approval without reauthorization when
    material

-   No payment above authorized amount

-   No payment if agreement has expired or changed materially

# 8. Human Escalation

Escalate when evidence is contradictory, the amount is high, the
requested remedy is outside policy, fraud indicators exist, or the
system cannot establish a reliable outcome.

# 9. Auditability

Every material AI decision should be reconstructable from the intent,
policy, authorization, tool call, result and transaction state.
