from odoo import api, models, fields, exceptions
from datetime import date, datetime

class ChangeJournal(models.Model):
	_name = "as.change_journal.wiz"
	_description = "Journal Changes"

	def _default_items(self):
		journal_ids = self._context.get('active_model') == 'asm.journal' and self._context.get('active_ids') or []
		return [
			(0, 0, {'journal_id': journal.id, 'note': journal.note})
			for journal in self.env['asm.journal'].browse(journal_ids)
		]

	item_ids = fields.One2many("as.change_journal.line", "wizard_id", string="Perubahan Jurnal", default=_default_items)

	def validate_change(self):
		for wiz in self:
			for item in wiz.item_ids:
				if item.note != '' and item.journal_id and not item.approved_date:
					item.journal_id.note = item.note
					item.write({
						'approved_date': datetime.now(),
						'user_id': self.env.user.id,
					})


class ChangeJournalLine(models.Model):
	_name = "as.change_journal.line"
	_description = "Journal Change Lines"

	wizard_id = fields.Many2one("as.change_journal.wiz", ondelete="cascade")
	user_id = fields.Many2one("res.users", ondelete="restrict", string="Diubah oleh", readonly=True)
	approved_date = fields.Datetime(string="Tanggal Perubahan", readonly=True)
	journal_id = fields.Many2one("asm.journal", ondelete="cascade", string="Jurnal", required=True)
	note = fields.Char(string="Keterangan", required=True)

	@api.onchange("journal_id")
	def _change_note(self):
		for line in self:
			if line.journal_id:
				line.note = line.journal_id.note