from odoo import models, fields, api

class TitleRncp(models.Model):
    _name = 'title.rncp'
    _description = 'Intitulé RNCP'

    name = fields.Char(string="Intitulé")
    code_rncp = fields.Char(string="Code RNCP")
    start_date = fields.Date(string="Date de début validitée")
    end_date = fields.Date(string="Date de fin de validitée")
    is_valid = fields.Boolean(string="Valide", default=True, compute='_compute_is_valid', store=True)

    @api.depends('start_date', 'end_date')
    def _compute_is_valid(self):
        for record in self:
            if record.end_date and record.end_date < fields.Date.today():
                record.is_valid = False
            else:
                record.is_valid = True
