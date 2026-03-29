Feature: Pipeline Logging
  As a dashboard user
  I want to view pipeline execution logs
  So that I can debug and monitor pipeline runs

  Background:
    Given the dashboard backend is running on port 8000

  # ============================================
  # HAPPY PATH SCENARIOS
  # ============================================

  @happy-path @critical
  Scenario: Logs are written during pipeline execution
    Given pipeline.log is reset to empty
    When I run a full pipeline job
    And the job completes
    Then pipeline.log should contain at least 2 log entries
    And each log entry should have required fields

  @happy-path @critical
  Scenario: Logs are visible via API
    Given pipeline.log contains 5 log entries
    When I GET "/api/v1/logs?page=1&page_size=50"
    Then the response status should be 200
    And the response should contain at least 5 logs
    And logs should be ordered by timestamp descending

  @happy-path
  Scenario: Filter logs by job_id
    Given logs exist for job "job-filter-abc-123"
    And logs exist for job "job-filter-xyz-789"
    When I GET "/api/v1/logs?job_id=job-filter-abc-123"
    Then the response status should be 200
    And all returned logs should have job_id "job-filter-abc-123"

  @happy-path
  Scenario: Filter logs by level
    Given logs exist with levels "info" and "error"
    When I GET "/api/v1/logs?level=error"
    Then the response status should be 200
    And all returned logs should have level "error"

  @happy-path
  Scenario: Get log statistics
    Given logs exist with various levels
    When I GET "/api/v1/logs/stats"
    Then the response status should be 200
    And the response should contain level counts

  @happy-path
  Scenario: Logs pagination works correctly
    Given 25 log entries exist
    When I GET "/api/v1/logs?page=1&page_size=10"
    Then the response should contain 10 logs
    When I GET "/api/v1/logs?page=2&page_size=10"
    Then the response should contain 10 different logs

  # ============================================
  # NEGATIVE SCENARIOS
  # ============================================

  @negative
  Scenario: Invalid log level filter returns validation error
    When I GET "/api/v1/logs?level=invalid_level_xyz"
    Then the response status should be 422

  @negative
  Scenario: Non-existent job_id filter returns empty
    When I GET "/api/v1/logs?job_id=completely-fake-job-id"
    Then the response status should be 200
    And the response should contain 0 logs

  @negative
  Scenario: Pipeline.log file missing returns empty
    Given pipeline.log file does not exist
    When I GET "/api/v1/logs"
    Then the response status should be 200
    And the response should have empty logs array

  @negative
  Scenario: Invalid pagination parameters are handled
    When I GET "/api/v1/logs?page=-1&page_size=0"
    Then the response status should be one of [200, 422]
    And no server crash should occur

  # ============================================
  # EDGE CASES
  # ============================================

  @edge-case
  Scenario: Log with very long message
    Given a log entry with 5000 character message exists
    When I GET "/api/v1/logs"
    Then the response status should be 200
    And the long message should be returned without truncation

  @edge-case
  Scenario: Log file with malformed JSON line
    Given pipeline.log contains one malformed JSON line
    When I GET "/api/v1/logs"
    Then the response status should be 200
    And valid logs should still be returned
