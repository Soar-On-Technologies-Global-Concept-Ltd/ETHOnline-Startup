import { BigInt, Bytes } from "@graphprotocol/graph-ts";
import {
  IntentCreated, IntentFunded, DisputeRaised, AIProposalSubmitted, AppealEscalated, IntentResolved,
  AbandonmentExecuted,
} from "../generated/IntentraEscrow/IntentraEscrow";
import { Provider, Intent } from "../generated/schema";

function key(intentId: BigInt): Bytes {
  return Bytes.fromByteArray(Bytes.fromBigInt(intentId));
}

function loadProvider(address: Bytes): Provider {
  let provider = Provider.load(address);
  if (provider == null) {
    provider = new Provider(address);
    provider.jobsFunded = 0;
    provider.jobsDelivered = 0;
    provider.jobsReleased = 0;
    provider.jobsSettled = 0;
    provider.jobsRefunded = 0;
    provider.disputes = 0;
    provider.evidenceAnchored = 0;          // the canonical escrow has no anchor call
    provider.paidOutMicroUsdc = BigInt.zero();
    provider.refundedMicroUsdc = BigInt.zero();
    provider.secondsToEvidenceTotal = BigInt.zero();
  }
  return provider as Provider;
}

export function handleIntentCreated(event: IntentCreated): void {
  const provider = loadProvider(event.params.provider);
  provider.save();

  const intent = new Intent(key(event.params.intentId));
  intent.intentId = event.params.intentId;
  intent.provider = provider.id;
  intent.customer = event.params.customer;
  intent.token = event.params.token;
  intent.amount = event.params.amount;
  intent.status = "AwaitingFunds";
  intent.createdAt = event.block.timestamp;
  intent.save();
}

export function handleIntentFunded(event: IntentFunded): void {
  const intent = Intent.load(key(event.params.intentId));
  if (intent == null) return;
  intent.status = "Funded";
  intent.fundedAt = event.block.timestamp;
  intent.save();

  const provider = loadProvider(intent.provider);
  provider.jobsFunded += 1;
  provider.save();
}

export function handleDisputeRaised(event: DisputeRaised): void {
  const intent = Intent.load(key(event.params.intentId));
  if (intent == null) return;
  intent.status = "InDispute";
  intent.disputedAt = event.block.timestamp;
  intent.save();

  const provider = loadProvider(intent.provider);
  provider.disputes += 1;
  provider.save();
}

export function handleAIProposalSubmitted(event: AIProposalSubmitted): void {
  const intent = Intent.load(key(event.params.intentId));
  if (intent == null) return;
  intent.status = "Timelocked";
  intent.proposedAt = event.block.timestamp;
  intent.toCustomer = event.params.customerAmount;
  intent.toProvider = event.params.providerAmount;
  intent.save();
}

export function handleAppealEscalated(event: AppealEscalated): void {
  const intent = Intent.load(key(event.params.intentId));
  if (intent == null) return;
  intent.status = "Appealed";
  intent.appealedAt = event.block.timestamp;
  intent.appealStake = event.params.stake;
  intent.save();
}

export function handleIntentResolved(event: IntentResolved): void {
  const intent = Intent.load(key(event.params.intentId));
  if (intent == null) return;
  intent.status = "Resolved";
  intent.closedAt = event.block.timestamp;
  intent.toCustomer = event.params.customerAmount;
  intent.toProvider = event.params.providerAmount;
  intent.save();

  const provider = loadProvider(intent.provider);
  provider.paidOutMicroUsdc = provider.paidOutMicroUsdc.plus(event.params.providerAmount);
  provider.refundedMicroUsdc = provider.refundedMicroUsdc.plus(event.params.customerAmount);
  if (event.params.customerAmount.isZero()) {
    provider.jobsReleased += 1;
    provider.jobsDelivered += 1;
  } else if (event.params.providerAmount.isZero()) {
    provider.jobsRefunded += 1;
  } else {
    provider.jobsSettled += 1;
  }
  provider.save();
}

export function handleAbandonmentExecuted(event: AbandonmentExecuted): void {
  const intent = Intent.load(key(event.params.intentId));
  if (intent == null) return;
  intent.status = "Abandoned";
  intent.closedAt = event.block.timestamp;
  intent.save();
}
