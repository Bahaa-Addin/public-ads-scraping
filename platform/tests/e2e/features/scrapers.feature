Feature: Scraper Status and Metrics
  As a dashboard user
  I want to monitor scraper health and performance
  So that I can ensure data collection is working

  Background:
    Given the dashboard backend is running on port 8000

  # ============================================
  # HAPPY PATH SCENARIOS
  # ============================================

  @happy-path @critical
  Scenario: Get scraper statuses
    When I GET "/api/v1/scrapers/status"
    Then the response status should be 200
    And the response should be an array
    And each item should have the following fields:
      | field         | type    |
      | source        | string  |
      | enabled       | boolean |
      | running       | boolean |
      | items_scraped | number  |
      | success_rate  | number  |
      | error_count   | number  |

  @happy-path @critical
  Scenario: Success rate is within valid range 0-100
    Given scraper status data exists
    When I GET "/api/v1/scrapers/status"
    Then the response status should be 200
    And each scraper success_rate should be between 0 and 100

  @happy-path
  Scenario: Last run timestamp updates after scraping
    Given the scraper "meta_ad_library" has last_run "2020-01-01T00:00:00"
    When I run a scrape job for source "meta_ad_library"
    And the job completes successfully
    Then the scraper "meta_ad_library" last_run should be updated
    And the new last_run should be more recent than "2020-01-01T00:00:00"

  @happy-path
  Scenario: Items scraped counter increments
    Given the scraper "meta_ad_library" has items_scraped 10
    When I run a scrape job for source "meta_ad_library" that returns items
    Then items_scraped for "meta_ad_library" should be greater than 10

  @happy-path
  Scenario: Get scraper metrics
    When I GET "/api/v1/scrapers/metrics"
    Then the response status should be 200
    And the response should be an array

  # ============================================
  # NEGATIVE SCENARIOS
  # ============================================

  @negative
  Scenario: Scraper status file corrupted returns defaults
    Given scraper_status.json contains invalid JSON
    When I GET "/api/v1/scrapers/status"
    Then the response status should be 200
    And the response should handle corrupted data gracefully

  @negative
  Scenario: Scraper service unavailable returns empty sessions
    Given the scraper service on port 3001 is not running
    When I GET "/api/v1/scrapers/active"
    Then the response status should be 200
    And the response should have empty sessions array

  @negative
  Scenario: Get status for invalid scraper source
    When I GET "/api/v1/scrapers/status?source=invalid_fake_source"
    Then the response status should be one of [200, 404]

  # ============================================
  # EDGE CASES
  # ============================================

  @edge-case
  Scenario: Success rate calculation with zero runs
    Given a scraper has never been run
    When I GET "/api/v1/scrapers/status"
    Then the response status should be 200
    And the response should not have division by zero errors

  @edge-case
  Scenario: Scraper running flag updates correctly
    When I start a scrape job for source "meta_ad_library"
    Then within 5 seconds the scraper running flag should be true
    When the scrape job completes
    Then the scraper running flag should be false

  @edge-case
  Scenario: Multiple scrapers have independent metrics
    Given "meta_ad_library" has items_scraped 100
    And "google_ads_transparency" has items_scraped 50
    When I run a scrape job for source "meta_ad_library" only
    Then "google_ads_transparency" items_scraped should still be 50
