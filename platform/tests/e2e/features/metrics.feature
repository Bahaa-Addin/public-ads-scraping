Feature: Dashboard Metrics and Time Series
  As a dashboard user
  I want to view metrics and charts
  So that I can monitor system performance

  Background:
    Given the dashboard backend is running on port 8000
    And metrics files are initialized

  # ============================================
  # HAPPY PATH SCENARIOS
  # ============================================

  @happy-path @critical
  Scenario: Time series endpoint returns valid data structure
    Given time_series.json contains data for metric "assets_scraped"
    When I GET "/api/v1/metrics/time-series/assets_scraped?hours=24"
    Then the response status should be 200
    And the response should have field "name" of type "string"
    And the response should have field "data" of type "array"
    And the response should have field "color" of type "string"

  @happy-path @critical
  Scenario: Dashboard metrics endpoint works
    When I GET "/api/v1/metrics/dashboard"
    Then the response status should be 200
    And the response should have field "pipeline" of type "object"
    And the response should have field "queue" of type "object"
    And the response should have field "system" of type "object"

  @happy-path
  Scenario: Industry distribution endpoint
    When I GET "/api/v1/metrics/industry-distribution"
    Then the response status should be 200
    And the response should be an array

  @happy-path
  Scenario: Time series data points have correct format
    Given time_series.json has valid data points
    When I GET "/api/v1/metrics/time-series/assets_scraped?hours=24"
    Then the response status should be 200
    And each data point should have "timestamp" as ISO 8601 string
    And each data point should have "value" as number

  # ============================================
  # NEGATIVE SCENARIOS
  # ============================================

  @negative
  Scenario: Invalid metric name returns empty data
    When I GET "/api/v1/metrics/time-series/completely_invalid_metric_xyz"
    Then the response status should be 200
    And the data array should be empty

  @negative
  Scenario: Time series file is empty dict
    Given time_series.json contains empty dict "{}"
    When I GET "/api/v1/metrics/time-series/assets_scraped"
    Then the response status should be 200
    And the data array should be empty

  @negative
  Scenario: Time series file is empty array
    Given time_series.json contains empty array "[]"
    When I GET "/api/v1/metrics/time-series/assets_scraped"
    Then the response status should be 200
    And the data array should be empty

  @negative
  Scenario: Invalid hours parameter
    When I GET "/api/v1/metrics/time-series/assets_scraped?hours=-1"
    Then the response status should be one of [200, 422]
    And no server error should occur

  # ============================================
  # EDGE CASES
  # ============================================

  @edge-case
  Scenario: Time series with only old data
    Given all time series data points are older than 48 hours
    When I GET "/api/v1/metrics/time-series/assets_scraped?hours=24"
    Then the response status should be 200
    And the data array should be empty
