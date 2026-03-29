import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import type {
  OrchestratorState,
  OrchestratorTaskState,
  SpecCoverageReport,
  TaskDefinition
} from './types.js';

function createTaskState(id: string): OrchestratorTaskState {
  return {
    id,
    status: 'PENDING',
    worktreeBranch: null,
    worktreePath: null,
    startedAt: null,
    completedAt: null,
    failureReason: null,
    notes: null,
    retryCount: 0
  };
}

function emptyCoverage(): SpecCoverageReport {
  return {
    totalRequirements: 0,
    coveredRequirements: 0,
    uncoveredRequirements: [],
    coveragePercentage: 0,
    unmappedTasks: [],
    timestamp: new Date().toISOString()
  };
}

function createFreshState(): OrchestratorState {
  return {
    version: '1.0.0',
    project: 'Public Ads Platform',
    mode: 'FULL',
    lastUpdated: new Date().toISOString(),
    iteration: 0,
    tasks: {},
    specCoverage: emptyCoverage(),
    qualityGates: {
      lint: { passed: false, lastRun: null },
      typecheck: { passed: false, lastRun: null },
      test: { passed: false, lastRun: null },
      security: { passed: false, lastRun: null },
      build: { passed: false, lastRun: null }
    }
  };
}

export class StateManager {
  private readonly statePath: string;

  constructor(projectRoot: string) {
    this.statePath = join(projectRoot, 'ORCHESTRATOR_STATE.json');
  }

  async load(): Promise<OrchestratorState> {
    try {
      const raw = await readFile(this.statePath, 'utf8');
      return JSON.parse(raw) as OrchestratorState;
    } catch {
      return createFreshState();
    }
  }

  async save(state: OrchestratorState): Promise<void> {
    state.lastUpdated = new Date().toISOString();
    await writeFile(this.statePath, JSON.stringify(state, null, 2) + '\n', 'utf8');
  }

  async syncTasks(state: OrchestratorState, tasks: TaskDefinition[]): Promise<OrchestratorState> {
    const activeTaskIds = new Set(tasks.map((task) => task.id));

    for (const task of tasks) {
      if (!state.tasks[task.id]) {
        state.tasks[task.id] = createTaskState(task.id);
      }
    }

    for (const id of Object.keys(state.tasks)) {
      if (!activeTaskIds.has(id)) {
        delete state.tasks[id];
      }
    }

    state.iteration += 1;
    await this.save(state);
    return state;
  }

  async updateCoverage(
    state: OrchestratorState,
    coverage: SpecCoverageReport
  ): Promise<OrchestratorState> {
    state.specCoverage = coverage;
    await this.save(state);
    return state;
  }

  getSummary(state: OrchestratorState): Record<string, number> {
    const statuses = Object.values(state.tasks).map((task) => task.status);

    return {
      total: statuses.length,
      pending: statuses.filter((status) => status === 'PENDING').length,
      ready: statuses.filter((status) => status === 'READY').length,
      inProgress: statuses.filter((status) => status === 'IN_PROGRESS').length,
      implemented: statuses.filter((status) => status === 'IMPLEMENTED').length,
      verified: statuses.filter((status) => status === 'VERIFIED').length,
      failed: statuses.filter((status) => status === 'FAILED').length,
      merged: statuses.filter((status) => status === 'MERGED').length
    };
  }
}
