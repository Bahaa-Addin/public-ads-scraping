Feature: Creative Assets Management
  As a dashboard user
  I want to view and manage scraped assets
  So that I can work with collected agentic ads

  Background:
    Given the dashboard backend is running on port 8000

  # ============================================
  # HAPPY PATH SCENARIOS
  # ============================================

  @happy-path
  Scenario: List assets when assets exist
    Given 10 assets exist in the database
    When I GET "/api/v1/assets?page=1&page_size=12"
    Then the response status should be 200
    And the response should contain assets
    And the response should have total count

  @happy-path
  Scenario: Get asset filter options
    Given assets exist with various industries and sources
    When I GET "/api/v1/assets/filters/options"
    Then the response status should be 200

  @happy-path
  Scenario: Filter assets by source
    Given assets exist from sources "meta_ad_library" and "google_ads"
    When I GET "/api/v1/assets?source=meta_ad_library"
    Then the response status should be 200
    And all returned assets should have source "meta_ad_library"

  # ============================================
  # NEGATIVE SCENARIOS
  # ============================================

  @negative @critical
  Scenario: Empty assets returns proper empty state
    Given assets.json contains empty array
    When I GET "/api/v1/assets"
    Then the response status should be 200
    And the response should have empty assets array
    And total should be 0

  @negative
  Scenario: Invalid asset ID returns 404
    When I GET "/api/v1/assets/completely-invalid-asset-id-xyz"
    Then the response status should be 404

  # ============================================
  # EDGE CASES
  # ============================================

  @edge-case
  Scenario: Assets with missing optional fields
    Given an asset exists without "industry" field
    When I GET "/api/v1/assets"
    Then the response status should be 200
    And the asset should be returned with null or default industry
