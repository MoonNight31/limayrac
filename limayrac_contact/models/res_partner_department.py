from odoo import models, fields

class ResPartnerDepartment(models.Model):
    _name = 'res.partner.department'
    _description = 'Service d\'un contact'

    name = fields.Char(string='Service', required=True)
    res_partner_id = fields.Many2one('res.partner', string='Structure', domain="[('is_company','=',True)]")
    active = fields.Boolean(default=True)
    is_blacklisted = fields.Boolean(default=False)
    reason_blacklist = fields.Text(string='Raison de la mise en blacklist')
    tags_ids = fields.Many2many('res.partner.category', string='Etiquettes')
    
    def action_blacklist(self):
        return {
            'name': 'Blacklist Service',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner.blacklist.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_partner_department_id': self.id,
            }
        }
    
    def action_unblacklist(self):
        self.is_blacklisted = False
        self.reason_blacklist = False

