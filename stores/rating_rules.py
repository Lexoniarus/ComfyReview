import math
from typing import Optional

# Was tut es?
# Reine Regel und Mathe Logik fuer Bewertungen.
# Keine DB, keine JSON, keine Router.
#
# Wo kommt es her?
# Inputs kommen aus DB Zeilen der Tabelle ratings: run, rating, deleted.
# success_threshold und delete_weight kommen aus Router Query Params oder Defaults.
#
# Wo geht es hin?
# Outputs gehen in Aggregationen in stores/analytics_combo.py und stores/analytics_params.py.

SUCCESS_THRESHOLD_DEFAULT = 4
DELETE_WEIGHT_DEFAULT = 5


def _rating_weight_for_run(run: int) -> int:
    # Was tut es?
    # Gewichtung fuer Rating Evidenz pro Run.
    #
    # Wo kommt es her?
    # run kommt aus ratings.run.
    #
    # Wo geht es hin?
    # Geht in success fail und avg_rating Gewichtung.
    r = max(1, int(run or 1))
    return int(r * r)


def _pass_min(run: int, base_pass_min: int) -> int:
    # Was tut es?
    # Erfolgs Schwelle je Run.
    #
    # Wo kommt es her?
    # run aus ratings.run.
    # base_pass_min aus success_threshold.
    #
    # Wo geht es hin?
    # Geht in _classify.
    r = max(1, int(run or 1))
    return int(min(10, int(base_pass_min) + (r - 1)))


def _fail_max(run: int) -> int:
    # Was tut es?
    # Fail Schwelle je Run.
    # Run 1 hat keinen Fail durch Rating, nur deletes.
    #
    # Wo kommt es her?
    # run aus ratings.run.
    #
    # Wo geht es hin?
    # Geht in _classify.
    r = max(1, int(run or 1))
    return int(0 if r <= 1 else min(10, r - 1))


def _delete_weight_for_run(run: int, base_delete_weight: int) -> int:
    # Was tut es?
    # Gewicht fuer deleted Runs je Run.
    # Spaetere Deletes werden weniger hart gewichtet, Minimum 1.
    #
    # Wo kommt es her?
    # run aus ratings.run.
    # base_delete_weight aus delete_weight.
    #
    # Wo geht es hin?
    # Geht als fail Gewicht in stats und recommendations.
    r = max(1, int(run or 1))
    return int(max(1, int(base_delete_weight) - (r - 1)))


def _classify(
    *,
    run: int,
    rating: Optional[int],
    deleted: int,
    base_pass_min: int,
) -> Optional[bool]:
    # Was tut es?
    # Klassifikation eines Runs.
    # True  Erfolg
    # False Fail
    # None  Neutral
    #
    # Wo kommt es her?
    # run rating deleted kommen aus der ratings DB.
    #
    # Wo geht es hin?
    # True False None gehen in success fail neutral Zaehler.
    if int(deleted or 0) == 1:
        return False
    if rating is None:
        return None

    r = max(1, int(run or 1))
    val = int(rating)

    if val >= _pass_min(r, base_pass_min):
        return True
    if r > 1 and val <= _fail_max(r):
        return False
    return None


def _sigmoid(x: float) -> float:
    # Was tut es?
    # Logit zu Wahrscheinlichkeit.
    #
    # Wo kommt es her?
    # x kommt aus additiven log odds in fetch_combo_predictions.
    #
    # Wo geht es hin?
    # pred_success Werte in recommendations approx.
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except Exception:
        return 0.0


def _bayes_lb05(success: float, fail_w: float) -> float:
    # Was tut es?
    # Konservativer Stabilitaetswert als lower bound Proxy.
    #
    # Wo kommt es her?
    # success und fail_w kommen aus Aggregation ueber ratings.
    # fail_w enthaelt auch delete weights.
    #
    # Wo geht es hin?
    # stability_lb05 in stats.html recommendations.html param_stats.html.
    a = float(int(success) + 1)
    b = float(int(fail_w) + 1)
    mean = a / (a + b)

    n = int(success) + int(fail_w)
    if n <= 0:
        return 0.0

    var = (a * b) / (((a + b) ** 2) * (a + b + 1.0))
    std = math.sqrt(max(0.0, var))
    return float(mean - 1.645 * std)