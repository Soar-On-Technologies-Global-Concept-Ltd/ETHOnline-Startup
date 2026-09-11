**Intentra --- Data Model & Security**

*Intentra*

Version: September 2026

# 1. Core Entities

  -----------------------------------------------------------------------
  Entity                              Purpose
  ----------------------------------- -----------------------------------
  User                                Person identity and preferences

  Organization                        Business or merchant account

  Team                                Business users

  Agent                               External/internal AI agent

  AgentPermission                     Agent authorization

  Policy                              Autonomy rules

  Merchant                            Business seller

  Professional                        Service provider

  Product                             Physical/digital item

  Service                             Professional service

  Quote                               Provider offer

  Transaction                         Canonical transaction

  Authorization                       Permission decision

  Payment                             Payment record

  Fulfillment                         Delivery/service progress

  Evidence                            Transaction evidence

  Complaint                           Issue report

  Dispute                             Contested outcome

  Refund                              Refund decision

  Resolution                          Final remedy

  ReputationEvent                     Trust signal

  AuditLog                            Security and activity history
  -----------------------------------------------------------------------

# 2. Data Classification

-   Public: provider profiles and approved catalog information

-   Internal: operational metrics

-   Confidential: agreements, transaction metadata, business data

-   Sensitive: identity/payment-related data and private evidence

# 3. Security Controls

-   Encryption in transit and at rest

-   Secrets manager

-   Least privilege

-   RBAC

-   API key rotation

-   Audit logs

-   Rate limits

-   Input validation

-   File type/size validation

-   Malware scanning for uploaded files

-   Database backups

-   Access monitoring

# 4. Privacy

-   Collect only data needed for the transaction.

-   Give users visibility into transaction records.

-   Provide deletion/export mechanisms where legally appropriate.

-   Do not expose private evidence to unrelated providers or agents.

-   Separate model context from persistent sensitive records.

# 5. AI Data Boundary

Do not automatically send the entire transaction database to an LLM.
Construct minimal task-specific context and redact unnecessary personal
or financial information.
