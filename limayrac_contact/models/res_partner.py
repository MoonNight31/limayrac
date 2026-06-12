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
    res_partner_naf_id = fields.Many2one(
        'res.partner.naf',
        string='Code NAF')
    
    headquarters_id = fields.Many2one('res.partner', string='Siège social', domain="[('is_company', '=', True), ('id', '!=', id)]")
    childs_company_ids = fields.One2many('res.partner', 'headquarters_id', string='Filiales')
