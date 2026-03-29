export type TaskStatus =
  | 'PENDING'
  | 'READY'
  | 'IN_PROGRESS'
  | 'IMPLEMENTED'
  | 'VERIFIED'
  | 'FAILED'
  | 'MERGED';

export interface LegacyTaskEntry {
  id: string;
  title: string;
  status: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  estimatedDuration: string;
  dependencies: string[];
  file?: string;
  files?: string[];
  requirements?: string[];
}

export interface LegacyPhaseEntry {
  id: string;
  name: string;
  tasks: LegacyTaskEntry[];
}

export interface LegacyState {
  phases: LegacyPhaseEntry[];
}

export interface TaskDefinition {
  id: string;
  title: string;
  phaseId: string;
  phaseName: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  estimatedDuration: string;
  dependencies: string[];
  filesTouched: string[];
  specRequirements: string[];
}

export interface SpecRequirement {
  id: string;
  text: string;
}

export interface SpecCoverageReport {
  totalRequirements: number;
  coveredRequirements: number;
  uncoveredRequirements: string[];
  coveragePercentage: number;
  unmappedTasks: string[];
  timestamp: string;
}

export interface QualityGateStatus {
  passed: boolean;
  lastRun: string | null;
}

export interface OrchestratorTaskState {
  id: string;
  status: TaskStatus;
  worktreeBranch: string | null;
  worktreePath: string | null;
  startedAt: string | null;
  completedAt: string | null;
  failureReason: string | null;
  notes: string | null;
  retryCount: number;
}

export interface OrchestratorState {
  version: string;
  project: string;
  mode: string;
  lastUpdated: string;
  iteration: number;
  tasks: Record<string, OrchestratorTaskState>;
  specCoverage: SpecCoverageReport;
  qualityGates: Record<'lint' | 'typecheck' | 'test' | 'security' | 'build', QualityGateStatus>;
}
