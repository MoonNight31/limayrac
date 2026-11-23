import logging

from odoo import models
from odoo.tools import convert_file

_logger = logging.getLogger(__name__)

# Fichiers de démo, dans l'ordre des dépendances.
DEMO_FILES = [
    'demo/title_rncp_demo.xml',
    'demo/limayrac_formations_demo.xml',
    'demo/res_partner_demo.xml',
    'demo/res_partner_department_demo.xml',
    'demo/res_partner_cursus_demo.xml',
    'demo/crm_lead_demo.xml',
    'demo/crm_opportunity_demo.xml',
]

# Opportunités de démo. Leur étape n'est pas forcée : elle est calculée
# automatiquement à partir de l'étudiant choisi et du contrat.
DEMO_OPPORTUNITIES = [
    'demo_opp_techcorp',
    'demo_opp_datasoft',
    'demo_opp_cloudnet',
    'demo_opp_pixelstudio',
    'demo_opp_retailplus',
    'demo_opp_webagence',
    'demo_lead_stage',
    'demo_lead_alternance',
    'demo_lead_sans_etudiant',
]


class LimayracDemoLoader(models.AbstractModel):
    _name = 'limayrac.demo.loader'
    _description = 'Chargeur des données de démo Limayrac'

    def load_demo_data(self):
        """Charge (ou met à jour) uniquement les données de démo du module.

        Appelable via l'action planifiée `ir.cron`. Utilise mode='update'
        pour être idempotent : relancer le cron réactualise les mêmes
        enregistrements au lieu de créer des doublons.
        """
        module = 'limayrac_contact'
        for filename in DEMO_FILES:
            _logger.info("Limayrac: chargement des données de démo %s", filename)
            convert_file(
                self.env,
                module,
                filename,
                idref=None,
                mode='update',
                noupdate=False,
            )
        self._reset_opportunity_revenue()
        _logger.info("Limayrac: données de démo chargées.")

    def _reset_opportunity_revenue(self):
        """Force expected_revenue = 0 sur les opportunités de démo.

        Les opportunités représentent des besoins d'entreprises en stagiaires /
        alternants, pas des ventes : aucun montant. Un champ retiré du XML n'est
        pas remis à zéro par convert_file en mode update, d'où cette remise à
        zéro explicite (idempotente) sur les enregistrements de démo existants.
        """
        leads = self.env['crm.lead']
        for xmlid in DEMO_OPPORTUNITIES:
            lead = self.env.ref(
                'limayrac_contact.%s' % xmlid, raise_if_not_found=False)
            if lead:
                leads |= lead
        if leads:
            leads.expected_revenue = 0
