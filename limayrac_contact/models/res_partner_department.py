from odoo import models, fields

class ResPartnerDepartment(models.Model):
    _name = 'res.partner.department'
    _description = 'Service d\'un contact'

    name = fields.Char(string='Service', required=True)
    res_partner_id = fields.Many2one('res.partner', string='Structure', domain="[('is_compagny','=',True)]")
    active = fields.Boolean(default=True)
    is_blacklisted = fields.Boolean(default=False)
    tags_ids = fields.Many2many('res.partner.category', string='Etiquettes')
    
    def action_blacklist(self):
        pass

