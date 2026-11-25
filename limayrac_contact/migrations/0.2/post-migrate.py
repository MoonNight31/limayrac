"""0.2 : RNCP, questions, responsables pédagogiques et formateurs passent sur la
formation. Chaque formation reprend la valeur de ses classes quand elles ont
toutes la même ; les classes gardent leurs valeurs."""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    groups = env['limayrac.formations.group'].with_context(active_test=False).search([])
    changed = groups._init_from_classes()
    _logger.info("Limayrac 0.2 : %d formation(s) complétée(s) depuis leurs classes", len(changed))
