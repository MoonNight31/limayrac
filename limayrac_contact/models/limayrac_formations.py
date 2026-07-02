from odoo import models, fields, api

class LimayracFormations(models.Model):
    _name = 'limayrac.formations'
    _description = 'Formations Limayrac'

    name = fields.Char(string="Nom commercial")
    question_one = fields.Char(string="Question 1")
    question_two = fields.Char(string="Question 2")
    question_three = fields.Char(string="Question 3")
    question_four = fields.Char(string="Question 4")
    question_five = fields.Char(string="Question 5")
    title_rncp_id = fields.Many2one('title.rncp', string="Titre RNCP", domain="[('is_valid', '=', True)]")
    old_rncp_ids = fields.Many2many('title.rncp', string="Ancien Titre RNCP", domain="[('is_valid', '=', False)]", readonly=True)
    res_partner_ids = fields.Many2many('res.partner', string='Responsables formation')

    @api.onchange('title_rncp_id')
    def _onchange_title_rncp_id(self):
        if self.title_rncp_id.id not in self.old_rncp_ids.ids:
            self.old_rncp_ids = [(4, self.title_rncp_id.id)]