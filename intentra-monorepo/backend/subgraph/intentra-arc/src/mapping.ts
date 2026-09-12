import { BigInt, Bytes } from "@graphprotocol/graph-ts";
import {
  JobFunded, EvidenceAnchored, Submitted, DisputeOpened, Released, Resolved, Refunded,
} from "../generated/IntentraEscrow/IntentraEscrow";
import { Provider, Job } from "../generated/schema";

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
    provider.evidenceAnchored = 0;
    provider.paidOutMicroUsdc = BigInt.zero();
    provider.refundedMicroUsdc = BigInt.zero();
    provider.secondsToEvidenceTotal = BigInt.zero();
  }
  return provider as Provider;
}

export function handleJobFunded(event: JobFunded): void {
  const provider = loadProvider(event.params.provider);
  provider.jobsFunded += 1;
  provider.save();

  const job = new Job(event.params.txKey);
  job.provider = provider.id;
  job.customer = event.params.customer;
  job.amount = event.params.amount;
  job.authorizationHash = event.params.authorizationHash;
  job.status = "Funded";
  job.fundedAt = event.block.timestamp;
  job.evidenceCount = 0;
  job.save();
}

export function handleEvidenceAnchored(event: EvidenceAnchored): void {
  const job = Job.load(event.params.txKey);
  if (job == null) return;
  job.evidenceCount += 1;
  const provider = loadProvider(job.provider);
  provider.evidenceAnchored += 1;
  if (job.firstEvidenceAt === null) {
    job.firstEvidenceAt = event.block.timestamp;
    provider.secondsToEvidenceTotal = provider.secondsToEvidenceTotal.plus(
      event.block.timestamp.minus(job.fundedAt));
  }
  provider.save();
  job.save();
}

export function handleSubmitted(event: Submitted): void {
  const job = Job.load(event.params.txKey);
  if (job == null) return;
  job.status = "Submitted";
  job.submittedAt = event.block.timestamp;
  job.releaseAfter = BigInt.fromU64(event.params.releaseAfter);
  job.save();

  const provider = loadProvider(job.provider);
  provider.jobsDelivered += 1;
  provider.save();
}

export function handleDisputeOpened(event: DisputeOpened): void {
  const job = Job.load(event.params.txKey);
  if (job == null) return;
  job.status = "Disputed";
  job.save();

  const provider = loadProvider(job.provider);
  provider.disputes += 1;
  provider.save();
}

export function handleReleased(event: Released): void {
  const job = Job.load(event.params.txKey);
  if (job == null) return;
  job.status = "Released";
  job.closedAt = event.block.timestamp;
  job.toProvider = event.params.amount;
  job.toCustomer = BigInt.zero();
  job.save();

  const provider = loadProvider(job.provider);
  provider.jobsReleased += 1;
  provider.paidOutMicroUsdc = provider.paidOutMicroUsdc.plus(event.params.amount);
  provider.save();
}

export function handleResolved(event: Resolved): void {
  const job = Job.load(event.params.txKey);
  if (job == null) return;
  job.status = "Resolved";
  job.closedAt = event.block.timestamp;
  job.toProvider = event.params.toProvider;
  job.toCustomer = event.params.toCustomer;
  job.outcomeHash = event.params.outcomeHash;
  job.save();

  const provider = loadProvider(job.provider);
  provider.jobsSettled += 1;
  provider.paidOutMicroUsdc = provider.paidOutMicroUsdc.plus(event.params.toProvider);
  provider.refundedMicroUsdc = provider.refundedMicroUsdc.plus(event.params.toCustomer);
  provider.save();
}

export function handleRefunded(event: Refunded): void {
  const job = Job.load(event.params.txKey);
  if (job == null) return;
  job.status = "Refunded";
  job.closedAt = event.block.timestamp;
  job.toProvider = BigInt.zero();
  job.toCustomer = event.params.amount;
  job.save();

  const provider = loadProvider(job.provider);
  provider.jobsRefunded += 1;
  provider.refundedMicroUsdc = provider.refundedMicroUsdc.plus(event.params.amount);
  provider.save();
}
