from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ResPartnerBlacklistWizard(models.TransientModel):
    _name = 'res.partner.blacklist.wizard'
    _description = 'Res Partner Blacklist Wizard'

    res_partner_department_id = fields.Many2one('res.partner.department', string='Service', required=True)
    reason = fields.Text(string='Raison de la mise en blacklist', required=True)


    def action_confirm(self):
        """Confirm blacklist and proceed with actual blacklist"""
        if self.res_partner_department_id:
            self.res_partner_department_id.is_blacklisted = True
            self.res_partner_department_id.reason_blacklist = self.reason