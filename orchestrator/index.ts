#!/usr/bin/env node

import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Planner } from './planner.js';
import { StateManager } from './stateManager.js';

interface Args {
  status: boolean;
  coverage: boolean;
  sync: boolean;
}

function parseArgs(argv: string[]): Args {
  return {
    status: argv.includes('--status'),
    coverage: argv.includes('--coverage'),
    sync: argv.includes('--sync')
  };
}

function isProjectRoot(candidate: string): boolean {
  return (
    existsSync(join(candidate, 'STATE.json')) &&
    existsSync(join(candidate, 'SPEC.md')) &&
    existsSync(join(candidate, 'ORCHESTRATOR_STATE.json'))
  );
}

function resolveProjectRoot(): string {
  const cwd = resolve(process.cwd());
  const moduleRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
  const candidates = [cwd, resolve(cwd, '..'), moduleRoot];

  for (const candidate of candidates) {
    if (isProjectRoot(candidate)) {
      return candidate;
    }
  }

  throw new Error(
    `Unable to resolve the repository root from ${cwd}. Expected STATE.json, SPEC.md, and ORCHESTRATOR_STATE.json to exist.`
  );
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const projectRoot = resolveProjectRoot();
  const planner = new Planner(projectRoot);
  const stateManager = new StateManager(projectRoot);
  const { tasks, coverage } = await planner.plan();

  if (args.coverage) {
    process.stdout.write('=== Agentic Ads SPEC Coverage ===\n\n');
    process.stdout.write(`Total requirements: ${coverage.totalRequirements}\n`);
    process.stdout.write(`Covered requirements: ${coverage.coveredRequirements}\n`);
    process.stdout.write(`Coverage: ${coverage.coveragePercentage}%\n`);
    process.stdout.write(
      `Uncovered requirements: ${coverage.uncoveredRequirements.join(', ') || 'none'}\n`
    );
    process.stdout.write(`Unmapped tasks: ${coverage.unmappedTasks.join(', ') || 'none'}\n`);
    return;
  }

  const state = await stateManager.load();
  await stateManager.syncTasks(state, tasks);
  await stateManager.updateCoverage(state, coverage);

  if (args.sync && !args.status) {
    process.stdout.write(`Synced ${tasks.length} tasks into ORCHESTRATOR_STATE.json\n`);
    process.stdout.write(`SPEC coverage: ${coverage.coveragePercentage}%\n`);
    return;
  }

  const summary = stateManager.getSummary(state);
  process.stdout.write('=== Agentic Ads Orchestrator Status ===\n\n');
  process.stdout.write(`Tasks tracked: ${summary.total}\n`);
  process.stdout.write(`Pending: ${summary.pending}\n`);
  process.stdout.write(`Ready: ${summary.ready}\n`);
  process.stdout.write(`In progress: ${summary.inProgress}\n`);
  process.stdout.write(`Implemented: ${summary.implemented}\n`);
  process.stdout.write(`Verified: ${summary.verified}\n`);
  process.stdout.write(`Failed: ${summary.failed}\n`);
  process.stdout.write(`Merged: ${summary.merged}\n\n`);
  process.stdout.write(`SPEC coverage: ${coverage.coveragePercentage}%\n`);
  process.stdout.write(
    `Uncovered requirements: ${coverage.uncoveredRequirements.join(', ') || 'none'}\n`
  );
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? (error.stack ?? error.message) : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
