import * as React from "react";
import { cn } from "@/lib/utils";

export interface TrustScoreBadgeProps {
  score: number;
  jobsCount?: number;
  className?: string;
}

export function TrustScoreBadge({ score, jobsCount, className }: TrustScoreBadgeProps) {
  const isHighTrust = score >= 90;
  const isMediumTrust = score >= 75 && score < 90;

  return (
    <div className={cn("inline-flex items-baseline gap-1.5 font-mono text-xs", className)}>
      <span
        className={cn("font-bold text-sm", {
          "text-success": isHighTrust,
          "text-warning": isMediumTrust,
          "text-danger": !isHighTrust && !isMediumTrust,
        })}
      >
        {score}% Trust Score
      </span>
      {jobsCount !== undefined && (
        <span className="text-text-muted text-[10px]">({jobsCount} Jobs Indexed on Graph)</span>
      )}
    </div>
  );
}
