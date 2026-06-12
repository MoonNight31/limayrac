from odoo import models, fields

class TitleRncp(models.Model):
    name = fields.Char(string="Intitulé")
    code_rncp = fields.Char(string="Code RNCP")
    start_date = fields.Date(string="Date de début validitée")
    end_date = fields.Date(strings="Date de fin de validitée")