from odoo import models, fields, api

class LimayracFormationsGroup(models.Model):
    _name = 'limayrac.formations.group'
    _description = 'Formation Limayrac'
    _order = 'name'

    name = fields.Char(string="Nom de la formation", required=True)
    active = fields.Boolean(default=True)
    filiere_id = fields.Many2one('limayrac.formations.filiere', string="Filière", required=True, ondelete='restrict', index=True)
    formation_ids = fields.One2many('limayrac.formations', 'group_id', string="Classes")
    formation_count = fields.Integer(string="Nombre de classes", compute='_compute_formation_count')

    # Contenu pédagogique de la formation. Il est copié dans chaque nouvelle
    # classe (voir limayrac.formations.create) : une classe garde ensuite ses
    # propres valeurs, même si la formation change.
    title_rncp_id = fields.Many2one('title.rncp', string="Titre RNCP", domain="[('is_valid', '=', True)]")
    old_rncp_ids = fields.Many2many(
        'title.rncp', 'limayrac_formations_group_old_rncp_rel', 'group_id', 'rncp_id',
        string="Ancien Titre RNCP", readonly=True)
    question_one = fields.Char(string="Question 1")
    question_two = fields.Char(string="Question 2")
    question_three = fields.Char(string="Question 3")
    question_four = fields.Char(string="Question 4")
    question_five = fields.Char(string="Question 5")
    res_partner_resp_ids = fields.Many2many(
        'res.partner', 'res_partner_limayrac_formations_group_resp_rel', 'group_id', 'res_partner_id',
        string='Responsables pédagogiques')
    res_partner_ids = fields.Many2many(
        'res.partner', 'res_partner_limayrac_formations_group_rel', 'group_id', 'res_partner_id',
        string='Formateurs')
    crm_lead_ids = fields.One2many('crm.lead', 'formation_id', string='Opportunités associées')
    crm_lead_ongoing_ids = fields.Many2many('crm.lead', string='Opportunités en cours', compute='_compute_crm_lead_ongoing_ids')

    _name_uniq = models.Constraint('UNIQUE(name)', "Cette formation existe déjà.")

    @api.depends('formation_ids')
    def _compute_formation_count(self):
        for record in self:
            record.formation_count = len(record.formation_ids)

    @api.depends('crm_lead_ids', 'crm_lead_ids.won_status')
    def _compute_crm_lead_ongoing_ids(self):
        for record in self:
            record.crm_lead_ongoing_ids = record.crm_lead_ids.filtered(
                lambda lead: lead.won_status == 'pending'
            )

    # Champs copiés dans une classe à sa création.
    CLASS_COPIED_FIELDS = (
        'title_rncp_id', 'question_one', 'question_two', 'question_three',
        'question_four', 'question_five', 'res_partner_resp_ids', 'res_partner_ids',
    )

    def _get_class_values(self):
        """Valeurs à copier dans une nouvelle classe de cette formation."""
        self.ensure_one()
        values = {}
        for name in self.CLASS_COPIED_FIELDS:
            field = self._fields[name]
            if field.type == 'many2many':
                values[name] = [fields.Command.set(self[name].ids)]
            elif field.type == 'many2one':
                values[name] = self[name].id
            else:
                values[name] = self[name]
        return values

    def write(self, vals):
        partners_before = self.res_partner_ids | self.res_partner_resp_ids
        if 'title_rncp_id' in vals:
            self._track_old_rncp(vals['title_rncp_id'])
        res = super().write(vals)
        if 'res_partner_ids' in vals or 'res_partner_resp_ids' in vals:
            partners_after = self.res_partner_ids | self.res_partner_resp_ids
            (partners_before | partners_after).modified(
                ['formation_group_ids', 'formation_group_resp_ids'])
        return res

    def _track_old_rncp(self, new_rncp_id):
        """Garde l'ancien titre RNCP dans l'historique quand il est remplacé."""
        for record in self:
            if record.title_rncp_id and record.title_rncp_id.id != new_rncp_id:
                record.old_rncp_ids = [fields.Command.link(record.title_rncp_id.id)]
            if new_rncp_id in record.old_rncp_ids.ids:
                record.old_rncp_ids = [fields.Command.unlink(new_rncp_id)]

    def _init_from_classes(self):
        """Reprise : remplit les champs vides de la formation avec la valeur de
        ses classes, quand toutes ses classes ont la même. Renvoie les
        formations modifiées."""
        changed = self.browse()
        for record in self:
            classes = record.with_context(active_test=False).formation_ids
            if not classes:
                continue
            vals = {}
            for name in self.CLASS_COPIED_FIELDS:
                if record[name]:
                    continue
                field = self._fields[name]
                if field.type == 'many2many':
                    distinct = {frozenset(c[name].ids) for c in classes}
                    if len(distinct) == 1 and next(iter(distinct)):
                        vals[name] = [fields.Command.set(list(next(iter(distinct))))]
                elif field.type == 'many2one':
                    distinct = {c[name].id for c in classes}
                    if len(distinct) == 1 and next(iter(distinct)):
                        vals[name] = next(iter(distinct))
                else:
                    distinct = {c[name] or False for c in classes}
                    if len(distinct) == 1 and next(iter(distinct)):
                        vals[name] = next(iter(distinct))
            if vals:
                record.write(vals)
                changed |= record
        return changed
