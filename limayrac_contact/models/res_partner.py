from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    birthday_date = fields.Date(string='Date de naissance')
    res_partner_department_ids = fields.One2many(
        'res.partner.department',
        'res_partner_id',
        string='Services')
    res_partner_naf_id = fields.Many2one(
        'res.partner.naf',
        string='Code NAF')