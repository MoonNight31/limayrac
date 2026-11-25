from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LimayracFormations(models.Model):
    _name = 'limayrac.formations'
    _description = 'Classes Limayrac'

    name = fields.Char(string="Nom commercial", required=True)
    group_id = fields.Many2one('limayrac.formations.group', string="Formation", required=True, ondelete='restrict', index=True)
    filiere_id = fields.Many2one(related='group_id.filiere_id', string="Filière", store=True, index=True)
    # Année d'études de la classe dans sa formation (1 = 1re année, ...).
    annee_niveau = fields.Integer(string="Année", required=True, default=1, aggregator=False)
    nb_annees = fields.Integer(related='group_id.nb_annees', string="Durée de la formation (années)")
    question_one = fields.Char(string="Question 1")
    question_two = fields.Char(string="Question 2")
    question_three = fields.Char(string="Question 3")
    question_four = fields.Char(string="Question 4")
    question_five = fields.Char(string="Question 5")
    title_rncp_id = fields.Many2one('title.rncp', string="Titre RNCP", domain="[('is_valid', '=', True)]")
    res_partner_resp_ids = fields.Many2many('res.partner', 'res_partner_limayrac_formations_resp_rel', 'limayrac_formations_id', 'res_partner_id', string='Responsables de sections')
    res_partner_ids = fields.Many2many('res.partner', 'res_partner_limayrac_formations_rel', 'limayrac_formations_id', 'res_partner_id', string='Formateurs')
    res_partner_cursus_ids = fields.One2many('res.partner.cursus', 'limayrac_formations_id', string='Cursus des contacts')

    # RNCP, questions, responsables pédagogiques et formateurs sont définis sur
    # la formation et copiés dans la classe à sa création ; la classe garde
    # ensuite ses propres valeurs (modifiables), même si la formation change.

    @api.constrains('annee_niveau', 'group_id')
    def _check_annee_niveau(self):
        for record in self:
            if not 1 <= record.annee_niveau <= record.group_id.nb_annees:
                raise ValidationError(_(
                    "La classe %(classe)s est en année %(annee)s, alors que la formation %(formation)s dure %(duree)s an(s).",
                    classe=record.name, annee=record.annee_niveau,
                    formation=record.group_id.name, duree=record.group_id.nb_annees))

    @staticmethod
    def _is_empty_value(value):
        if not value:
            return True
        if isinstance(value, (list, tuple)):
            # Commandes x2many vides : [] ou [Command.set([])] / [Command.clear()]
            return all(isinstance(cmd, (list, tuple)) and (
                (cmd[0] == fields.Command.SET and not cmd[2]) or cmd[0] == fields.Command.CLEAR)
                for cmd in value)
        return False

    @api.model_create_multi
    def create(self, vals_list):
        Group = self.env['limayrac.formations.group']
        for vals in vals_list:
            group = Group.browse(vals.get('group_id'))
            if not group:
                continue
            for name, value in group._get_class_values().items():
                if self._is_empty_value(vals.get(name)):
                    vals[name] = value
        records = super().create(vals_list)
        (records.res_partner_ids | records.res_partner_resp_ids).modified(
            ['limayrac_formations_ids', 'limayrac_formations_resp_ids'])
        return records

    @api.onchange('group_id')
    def _onchange_group_id_copy(self):
        # Nouvelle classe : on pré-remplit depuis la formation pour que
        # l'utilisateur voie (et puisse ajuster) ce qui sera enregistré.
        if self._origin.id or not self.group_id:
            return
        group = self.group_id
        for name in group.CLASS_COPIED_FIELDS:
            if not self[name]:
                self[name] = group[name]

    def write(self, vals):
        partners_before = self.res_partner_ids | self.res_partner_resp_ids
        res = super(LimayracFormations, self).write(vals)
        if 'res_partner_ids' in vals or 'res_partner_resp_ids' in vals:
            partners_after = self.res_partner_ids | self.res_partner_resp_ids
            (partners_before | partners_after).modified(['limayrac_formations_ids', 'limayrac_formations_resp_ids'])
        return res

    def unlink(self):
        partners = self.res_partner_ids | self.res_partner_resp_ids
        res = super(LimayracFormations, self).unlink()
        partners.modified(['limayrac_formations_ids', 'limayrac_formations_resp_ids'])
        return res