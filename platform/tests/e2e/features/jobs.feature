Feature: Job Lifecycle Management
  As a dashboard user
  I want to manage and monitor jobs
  So that I can track pipeline execution

  Background:
    Given the dashboard backend is running on port 8000
    And the agent API is running on port 8081
    And the scraper service is running on port 3001

  # ============================================
  # HAPPY PATH SCENARIOS
  # ============================================

  @happy-path @critical
  Scenario: Create and complete a scrape job
    Given the data files are reset to clean state
    When I POST to "/api/v1/jobs/scrape" with payload:
      """
      {
        "sources": ["meta_ad_library"],
        "query": "test",
        "limit": 5
      }
      """
    Then the response status should be 200
    And the response should contain a "job_id" field
    And within 10 seconds the job status should be "in_progress"
    And within 120 seconds the job status should be "completed"
    And the job should have a "started_at" timestamp
    And the job should have a "completed_at" timestamp
    And "completed_at" should be after "started_at"

  @happy-path @critical
  Scenario: Create and complete a full pipeline job
    Given the data files are reset to clean state
    When I POST to "/api/v1/jobs/pipeline" with payload:
      """
      {
        "sources": ["meta_ad_library"],
        "query": "real estate",
        "limit": 3,
        "skip_steps": []
      }
      """
    Then the response status should be 200
    And the response should contain a "job_id" field
    And within 10 seconds the job status should be "in_progress"
    And within 180 seconds the job status should be "completed"

  @happy-path
  Scenario: List jobs with pagination
    Given 5 completed jobs exist in the database
    When I GET "/api/v1/jobs?page=1&page_size=3"
    Then the response status should be 200
    And the response should contain exactly 3 jobs
    And the response should have "total" greater than or equal to 5

  @happy-path
  Scenario: Get job by ID
    Given a job with id "test-job-get-123" exists with status "completed"
    When I GET "/api/v1/jobs/test-job-get-123"
    Then the response status should be 200
    And the response should contain job details with id "test-job-get-123"

  @happy-path
  Scenario: Get job statistics by status
    Given jobs exist with various statuses
    When I GET "/api/v1/jobs/stats/by-status"
    Then the response status should be 200
    And the response should contain status counts

  # ============================================
  # NEGATIVE SCENARIOS
  # ============================================

  @negative
  Scenario: Create job with invalid source
    When I POST to "/api/v1/jobs/scrape" with payload:
      """
      {
        "sources": ["invalid_nonexistent_source"],
        "limit": 10
      }
      """
    Then the response status should be 200
    And the response should contain a "job_id" field

  @negative
  Scenario: Create job with empty sources
    When I POST to "/api/v1/jobs/scrape" with payload:
      """
      {
        "sources": [],
        "limit": 10
      }
      """
    Then the response status should be 200

  @negative
  Scenario: Get non-existent job
    When I GET "/api/v1/jobs/non-existent-job-id-12345"
    Then the response status should be 404

  @negative
  Scenario: Create job with negative limit
    When I POST to "/api/v1/jobs/scrape" with payload:
      """
      {
        "sources": ["meta_ad_library"],
        "limit": -5
      }
      """
    Then the response status should be 200

  @negative @slow
  Scenario: Job creation succeeds even if services unavailable
    When I POST to "/api/v1/jobs/scrape" with payload:
      """
      {
        "sources": ["meta_ad_library"],
        "limit": 5
      }
      """
    Then the response status should be 200
    And the response should contain a "job_id" field

  # ============================================
  # EDGE CASES
  # ============================================

  @edge-case
  Scenario: Job with maximum limit
    When I POST to "/api/v1/jobs/scrape" with payload:
      """
      {
        "sources": ["meta_ad_library"],
        "limit": 1000
      }
      """
    Then the response status should be 200
    And the response should contain a "job_id" field

  @edge-case
  Scenario: Job with special characters in query
    When I POST to "/api/v1/jobs/scrape" with payload:
      """
      {
        "sources": ["meta_ad_library"],
        "query": "test & <script>alert(1)</script>",
        "limit": 5
      }
      """
    Then the response status should be 200
    And the response should contain a "job_id" field

  @edge-case
  Scenario: Concurrent job creation
    When I create 3 jobs simultaneously
    Then all 3 jobs should be created with unique IDs
    And all jobs should have valid status

  @edge-case
  Scenario: Job timestamps are in correct format
    Given the data files are reset to clean state
    When I POST to "/api/v1/jobs/scrape" with payload:
      """
      {
        "sources": ["meta_ad_library"],
        "query": "timestamp test",
        "limit": 3
      }
      """
    Then the response status should be 200
    And the job should have timestamps in ISO 8601 format

  @edge-case
  Scenario: Job status transitions are valid
    Given the data files are reset to clean state
    When I create and monitor a job
    Then the job status should only transition through valid states
