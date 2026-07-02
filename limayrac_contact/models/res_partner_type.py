from odoo import models, fields, api

class ResPartnerType(models.Model):
    _name = 'res.partner.type'
    _description = 'Res Partner Type'

    name = fields.Char(string='Nom',)
    code = fields.Char(string='Code')
