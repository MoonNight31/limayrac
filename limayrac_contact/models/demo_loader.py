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

# Étape cible de chaque opportunité de démo. crm.lead.create() force toujours
# stage_lead1 (pas de res_partner_id), donc on applique l'étape voulue après
# chargement via un write() qui ne touche pas à res_partner_id.
OPPORTUNITY_STAGES = {
    'demo_opp_techcorp': 'crm.stage_lead3',
    'demo_opp_datasoft': 'crm.stage_lead2',
    'demo_opp_cloudnet': 'crm.stage_lead2',
    'demo_opp_pixelstudio': 'crm.stage_lead1',
    'demo_opp_retailplus': 'crm.stage_lead3',
    'demo_opp_webagence': 'crm.stage_lead4',
}


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
        self._set_opportunity_stages()
        self._reset_opportunity_revenue()
        _logger.info("Limayrac: données de démo chargées.")

    def _reset_opportunity_revenue(self):
        """Force expected_revenue = 0 sur les opportunités de démo.

        Les opportunités représentent des besoins d'entreprises en stagiaires /
        alternants, pas des ventes : aucun montant. Un champ retiré du XML n'est
        pas remis à zéro par convert_file en mode update, d'où cette remise à
        zéro explicite (idempotente) sur les enregistrements de démo existants.
        """
        xmlids = list(OPPORTUNITY_STAGES) + [
            'demo_lead_stage', 'demo_lead_alternance', 'demo_lead_sans_etudiant',
        ]
        leads = self.env['crm.lead']
        for xmlid in xmlids:
            lead = self.env.ref(
                'limayrac_contact.%s' % xmlid, raise_if_not_found=False)
            if lead:
                leads |= lead
        if leads:
            leads.expected_revenue = 0

    def _set_opportunity_stages(self):
        """Applique l'étape cible à chaque opportunité de démo.

        crm.lead.create() force stage_lead1/stage_lead2 selon res_partner_id ;
        comme les opportunités de démo n'ont pas d'étudiant associé, elles
        arrivent toutes en stage_lead1. On corrige ici via un write() qui ne
        touche pas à res_partner_id (sinon l'étape serait recalculée).
        """
        for xmlid, stage_xmlid in OPPORTUNITY_STAGES.items():
            lead = self.env.ref(
                'limayrac_contact.%s' % xmlid, raise_if_not_found=False)
            stage = self.env.ref(stage_xmlid, raise_if_not_found=False)
            if lead and stage:
                lead.stage_id = stage
