# routers/playground_router.py
#
# Zweck
# Dieser File bleibt als stabile Import-Quelle fuer app.py erhalten.
# Der eigentliche Code liegt jetzt unter routers/playground/*.
#
# Wichtig
# app.py kann weiterhin:
#   from routers.playground_router import router as playground_router
#
# nutzen, ohne dass man dort etwas aendern muss.

from routers.playground import router  # noqa: F401
