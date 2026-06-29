from odoo import models, fields

class ServicesNeeds(models.Model):
    _name = 'services.needs'
    _description = 'Besoins des services'

    title_need = fields.Char(string='Titre du besoin')
    description_need = fields.Text(string='Description du besoin')
    date_expiration = fields.Date(string='Date d\'expiration du besoin')