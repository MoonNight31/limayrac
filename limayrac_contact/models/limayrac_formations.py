from odoo import models, fields

class LimayracFormations(models.Model):
    _name = 'limayrac.formations'
    _description = 'Formations Limayrac'

    name = fields.Char(string="Nom commercial")
    question_one = fields.Char(string="Question 1")
    question_two = fields.Char(string="Question 2")
    question_three = fields.Char(string="Question 3")
    question_four = fields.Char(string="Question 4")
    question_five = fields.Char(string="Question 5")
    title_rncp_id = fields.Many2one('title.rncp', string="Titre RNCP")
    res_partner_ids = fields.Many2many('res.partner', string='Responsables formation')