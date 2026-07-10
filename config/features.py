"""Feature-flag config — where resolved flag values persist.

`database` (the `features` table) persists across processes/restarts, which is what makes a
runtime toggle (a console command, a portal call) visible to the running web workers without a
redeploy — the in-memory `array` driver can't cross that boundary.
"""

config = {
    "driver": "database",
}
