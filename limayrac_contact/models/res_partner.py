from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    birthday_date = fields.Date(string='Date de naissance')
    res_partner_department_ids = fields.One2many(
        'res.partner.department',
        'res_partner_id',
        string='Services')
    is_partenaire = fields.Boolean(default=False)
    is_prospect = fields.Boolean(default=False)
    is_blacklist = fields.Boolean(default=False)