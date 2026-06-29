from odoo import models, fields

class TitleRncp(models.Model):
    _name = 'title.rncp'
    _description = 'Intitulé RNCP'

    name = fields.Char(string="Intitulé")
    code_rncp = fields.Char(string="Code RNCP")
    start_date = fields.Date(string="Date de début validitée")
    end_date = fields.Date(string="Date de fin de validitée")
    
