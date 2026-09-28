from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    res_partner_id = fields.Many2one('res.partner', string='Etudiant associé', domain="[('is_company', '=', False), ('partner_type_ids.code', '=', 'type_002')]")
    type_contract = fields.Selection([('1', 'Stage'), ('2', 'Alternance'), ('3', 'Stage/Alternance')], string='Type de contrat')
    limayrac_formation_ids = fields.Many2many('limayrac.formations', 'crm_lead_limayrac_formations_rel', 'crm_lead_id', 'limayrac_formations_id', string='Formations Limayrac')
    contract_ids = fields.One2many('limayrac.contract', 'crm_lead_id', string='Contrats')
    contract_count = fields.Integer(compute='_compute_contract_count')

    @api.depends('contract_ids')
    def _compute_contract_count(self):
        for record in self:
            record.contract_count = len(record.contract_ids)

    def action_create_contract(self):
        """Ouvre un formulaire de contrat pré-rempli avec ce que l'opportunité sait déjà."""
        self.ensure_one()
        student = self.res_partner_id
        cursus = student.res_partner_cursus_ids.filtered(
            lambda c: not c.end_date or c.end_date >= fields.Date.today())
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouveau contrat',
            'res_model': 'limayrac.contract',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_crm_lead_id': self.id,
                'default_student_id': student.id,
                'default_company_partner_id': self.partner_id.commercial_partner_id.id,
                # type_contract vaut '3' (Stage/Alternance) sur l'opportunité :
                # il faut trancher au moment du contrat, on ne pré-remplit pas.
                'default_contract_type': self.type_contract if self.type_contract in ('1', '2') else False,
                'default_cursus_id': cursus.id if len(cursus) == 1 else False,
                'default_limayrac_formation_id': cursus.limayrac_formations_id.id if len(cursus) == 1 else False,
            },
        }

    def action_view_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contrats',
            'res_model': 'limayrac.contract',
            'view_mode': 'list,form',
            'domain': [('crm_lead_id', '=', self.id)],
            'context': {'default_crm_lead_id': self.id},
        }

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