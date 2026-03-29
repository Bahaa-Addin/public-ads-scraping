Feature: Server-Sent Events for Real-time Updates
  As a dashboard user
  I want to receive real-time pipeline updates
  So that I can monitor job progress live

  Background:
    Given the dashboard backend is running on port 8000

  # ============================================
  # HAPPY PATH SCENARIOS
  # ============================================

  @happy-path @critical
  Scenario: SSE stream connects successfully
    When I connect to SSE endpoint "/api/v1/events/stream"
    Then the SSE connection should be established
    And I should receive a "connected" event type

  @happy-path @critical
  Scenario: Events are emitted during job execution
    Given I am connected to the SSE event stream
    When I start a scrape job
    Then I should receive events with types including "step_started"

  @happy-path
  Scenario: Event history is preserved on reconnection
    Given events were emitted for a recent job
    When I disconnect and reconnect to the SSE stream
    Then I should receive some historical events

  # ============================================
  # NEGATIVE SCENARIOS
  # ============================================

  @negative
  Scenario: SSE stream handles client disconnect gracefully
    When I connect to SSE and immediately disconnect
    Then the server should not crash
    And subsequent connections should still work

  # ============================================
  # EDGE CASES
  # ============================================

  @edge-case
  Scenario: Multiple clients receive same events
    Given 2 clients are connected to the SSE stream
    When a job event is emitted
    Then both clients should receive the event
