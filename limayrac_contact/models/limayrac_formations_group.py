from odoo import models, fields, api

class LimayracFormationsGroup(models.Model):
    _name = 'limayrac.formations.group'
    _description = 'Formation Limayrac'
    _order = 'name'

    name = fields.Char(string="Nom de la formation", required=True)
    active = fields.Boolean(default=True)
    filiere_id = fields.Many2one('limayrac.formations.filiere', string="Filière", required=True, ondelete='restrict', index=True)
    formation_ids = fields.One2many('limayrac.formations', 'group_id', string="Classes")
    formation_count = fields.Integer(string="Nombre de classes", compute='_compute_formation_count')
    crm_lead_ids = fields.One2many('crm.lead', 'formation_id', string='Opportunités associées')
    crm_lead_ongoing_ids = fields.Many2many('crm.lead', string='Opportunités en cours', compute='_compute_crm_lead_ongoing_ids')

    _name_uniq = models.Constraint('UNIQUE(name)', "Cette formation existe déjà.")

    @api.depends('formation_ids')
    def _compute_formation_count(self):
        for record in self:
            record.formation_count = len(record.formation_ids)

    @api.depends('crm_lead_ids', 'crm_lead_ids.won_status')
    def _compute_crm_lead_ongoing_ids(self):
        for record in self:
            record.crm_lead_ongoing_ids = record.crm_lead_ids.filtered(
                lambda lead: lead.won_status == 'pending'
            )
