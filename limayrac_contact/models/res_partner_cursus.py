from odoo import models, fields

class ResPartnerCursus(models.Model):
    _name = 'res.partner.cursus'
    _description = 'Cursus d\'un contact'

    start_date = fields.Date(string='Date de début', required=True)
    end_date = fields.Date(string='Date de fin')
    res_partner_id = fields.Many2one('res.partner', string='Contact', required=True)
    limayrac_formations_id = fields.Many2one('limayrac.formations', string='Formation', required=True)
    is_diploma_obtained = fields.Boolean(string='Diplôme obtenu')
