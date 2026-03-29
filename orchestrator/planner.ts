import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { SpecCoverageEngine } from './specCoverage.js';
import type { LegacyState, TaskDefinition } from './types.js';

export class Planner {
  private readonly statePath: string;
  private readonly specEngine: SpecCoverageEngine;

  constructor(private readonly projectRoot: string) {
    this.statePath = join(projectRoot, 'STATE.json');
    this.specEngine = new SpecCoverageEngine(join(projectRoot, 'SPEC.md'));
  }

  async loadTasks(): Promise<TaskDefinition[]> {
    const raw = await readFile(this.statePath, 'utf8');
    const state = JSON.parse(raw) as LegacyState;
    const tasks: TaskDefinition[] = [];

    for (const phase of state.phases) {
      for (const task of phase.tasks) {
        const filesTouched = task.files ?? (task.file ? [task.file] : []);
        tasks.push({
          id: task.id,
          title: task.title,
          phaseId: phase.id,
          phaseName: phase.name,
          priority: task.priority,
          estimatedDuration: task.estimatedDuration,
          dependencies: task.dependencies,
          filesTouched,
          specRequirements: task.requirements ?? []
        });
      }
    }

    return tasks;
  }

  async plan(): Promise<{
    tasks: TaskDefinition[];
    coverage: Awaited<ReturnType<SpecCoverageEngine['compute']>>;
  }> {
    const tasks = await this.loadTasks();
    const coverage = await this.specEngine.compute(tasks);

    return { tasks, coverage };
  }
}
