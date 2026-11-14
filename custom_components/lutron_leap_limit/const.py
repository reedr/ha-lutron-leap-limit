"""Constants for Lutron LEAP Limit."""

DOMAIN = "lutron_leap_limit"

# pylutron-caseta 0.29.0 uses 256 KiB.
LIMIT = 4 * 1024 * 1024

# pylutron-caseta 0.29.0 waits 5 s for each command's reply. A HomeWorks QS
# processor sent a burst of zone commands (Goodnight: every light in a room)
# answers some of them after 5-10 s: the light changes, but the call fails
# with TimeoutError and the late reply is logged as "Was not expecting message".
REQUEST_TIMEOUT = 15.0

ISSUE_INCOMPATIBLE = "incompatible"
ISSUE_NOT_NEEDED = "not_needed"
