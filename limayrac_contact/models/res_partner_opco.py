from odoo import models, fields


class ResPartnerOpco(models.Model):
    _name = 'res.partner.opco'
    _description = 'OPCO (opérateur de compétences)'
    _order = 'name'

    name = fields.Char(string='OPCO', required=True)
    active = fields.Boolean(default=True)
    company_ids = fields.One2many('res.partner', 'res_partner_opco_id', string='Entreprises')

    _name_uniq = models.Constraint('UNIQUE(name)', "Cet OPCO existe déjà.")
