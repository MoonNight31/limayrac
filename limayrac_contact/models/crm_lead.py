from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    res_partner_id = fields.Many2one('res.partner', string='Etudiant associé', domain="[('is_company', '=', False), ('partner_type_ids.code', '=', 'type_002')]")
    type_contract = fields.Selection([('1', 'Stage'), ('2', 'Alternance'), ('3', 'Stage/Alternance')], string='Type de contrat')
    limayrac_formation_ids = fields.Many2many('limayrac.formations', 'crm_lead_limayrac_formations_rel', 'crm_lead_id', 'limayrac_formations_id', string='Formations Limayrac')

    def _stage_for_partner(self, has_partner):
        xmlid = 'crm.stage_lead2' if has_partner else 'crm.stage_lead1'
        return self.env.ref(xmlid)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.stage_id = record._stage_for_partner(bool(record.res_partner_id))
        return records

    def write(self, vals):
        res = super().write(vals)
        # Ne réagir qu'à un vrai changement de l'étudiant associé,
        # pas à chaque enregistrement du formulaire.
        if 'res_partner_id' in vals:
            for record in self:
                record.stage_id = record._stage_for_partner(bool(record.res_partner_id))
        return res