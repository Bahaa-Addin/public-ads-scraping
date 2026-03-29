import { readFile } from 'node:fs/promises';
import type { SpecCoverageReport, SpecRequirement, TaskDefinition } from './types.js';

const REQUIREMENT_ROW = /\|\s*((?:FR|NFR)-\d+\.\d+)\s*\|\s*(.+?)\s*\|/;

export function parseSpecRequirements(specContent: string): SpecRequirement[] {
  const requirements: SpecRequirement[] = [];

  for (const line of specContent.split('\n')) {
    const match = line.match(REQUIREMENT_ROW);
    if (!match) {
      continue;
    }

    const [id, text] = match.slice(1);
    requirements.push({
      id,
      text: text.trim()
    });
  }

  return requirements;
}

export class SpecCoverageEngine {
  constructor(private readonly specPath: string) {}

  async loadRequirements(): Promise<SpecRequirement[]> {
    const content = await readFile(this.specPath, 'utf8');
    return parseSpecRequirements(content);
  }

  async compute(tasks: TaskDefinition[]): Promise<SpecCoverageReport> {
    const requirements = await this.loadRequirements();
    const taskIdsWithRequirements = new Set<string>();
    const coveredRequirements = new Set<string>();

    for (const task of tasks) {
      if (task.specRequirements.length > 0) {
        taskIdsWithRequirements.add(task.id);
      }

      for (const requirement of task.specRequirements) {
        coveredRequirements.add(requirement);
      }
    }

    const uncoveredRequirements = requirements
      .map((requirement) => requirement.id)
      .filter((id) => !coveredRequirements.has(id))
      .sort();

    const unmappedTasks = tasks
      .filter((task) => !taskIdsWithRequirements.has(task.id))
      .map((task) => task.id)
      .sort();

    const totalRequirements = requirements.length;
    const matchedRequirements = requirements.filter((requirement) =>
      coveredRequirements.has(requirement.id)
    ).length;

    return {
      totalRequirements,
      coveredRequirements: matchedRequirements,
      uncoveredRequirements,
      coveragePercentage:
        totalRequirements === 0
          ? 100
          : Math.round((matchedRequirements / totalRequirements) * 10000) / 100,
      unmappedTasks,
      timestamp: new Date().toISOString()
    };
  }
}
