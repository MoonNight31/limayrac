from odoo import models, fields, api

class ResPartnerNaf(models.Model):
    _name = 'res.partner.naf'
    _description = 'Res Partner NAF'

    name = fields.Char(string='Code NAF', compute='_compute_name', store=True)
    code = fields.Char(string='Code NAF', required=True)
    activity = fields.Char(string='Activité', required=True)

    @api.depends('code', 'activity')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.code} - {record.activity}"