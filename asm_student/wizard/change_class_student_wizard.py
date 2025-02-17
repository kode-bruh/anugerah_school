from odoo import api, models, fields, exceptions
from datetime import date, datetime, timedelta

class ChangeClassStudentWizard(models.TransientModel):
	_name = "as.class_student.wiz"
	_description = "Class History Wizard"

	student_id = fields.Many2one("asm.student", ondelete="cascade", string="Siswa", required=True)

	class_to_add_ids = fields.One2many("as.class_student.add", "wizard_id")
	class_to_edit_ids = fields.One2many("as.class_student.edit", "wizard_id")
	class_to_delete_ids = fields.Many2many("as.class_student", domain="[('student_id', '=', student_id)]")

	@api.onchange("student_id")
	def _reset_all(self):
		for wiz in self:
			wiz.class_to_add_ids = [(5, 0, 0)]
			wiz.class_to_edit_ids = [(5, 0, 0)]
			wiz.class_to_delete_ids = [(5, 0, 0)]

	def validate_changes(self):
		for wiz in self:
			if not wiz.student_id:
				raise exceptions.UserError("Siswa harus dipilih sebelum validasi perubahan.")
			now = (datetime.now() + timedelta(hours=7)).strftime('%d %B %Y %H:%M')
			# Deletion of class student
			text = "Kelas Siswa dihapus oleh <b>%s</b> pada <b>%s</b>.<ul>" % (self.env.user.partner_id.name, now)
			for i in wiz.class_to_delete_ids:
				text += "<li>%s</li>" % i.class_id.display_name
				i.sudo().unlink()
			text += "</ul>"
			self.env['mail.message'].create({
				'subject': 'Class Removed',
				'date': datetime.now(),
				'author_id': self.env.user.partner_id.id,
				'model': 'asm.student',
				'res_id': wiz.student_id.id,
				'message_type': 'notification',
				'subtype_id': self.env.ref('mail.mt_note').id,
				'body': text,
 			})

			# Adding class student
			text = "Kelas Siswa ditambahkan oleh <b>%s</b> pada <b>%s</b>.<ul>" % (self.env.user.partner_id.name, now)
			for i in wiz.class_to_add_ids:
				self.env['as.class_student'].sudo().create({
					'class_id': i.class_id.id,
					'student_id': wiz.student_id.id,
					'term_id': i.term_id.id,
					'year_in': i.term_id.year_in,
					'year_out': i.term_id.year_out,
				})
				text += "<li>%s</li>" % i.class_id.name
			text += "</ul>"
			if len(wiz.class_to_add_ids) > 0:
				self.env['mail.message'].create({
					'subject': 'Class Removed',
					'date': datetime.now(),
					'author_id': self.env.user.partner_id.id,
					'model': 'asm.student',
					'res_id': wiz.student_id.id,
					'message_type': 'notification',
					'subtype_id': self.env.ref('mail.mt_note').id,
					'body': text,
	 			})

			# Edit class student
			text = "Kelas Siswa telah dihapus oleh <b>%s</b> pada <b>%s</b>.<ul>" % (self.env.user.partner_id.name, now)
			for i in wiz.class_to_edit_ids:
				i.class_student_id.sudo().write({
					'term_id': i.term_id.id,
				})
				text += "<li>%s</li>" % i.class_student_id.class_id.display_name
			text += "</ul>"
			if len(wiz.class_to_edit_ids) > 0:
				self.env['mail.message'].create({
					'subject': 'Class Removed',
					'date': datetime.now(),
					'author_id': self.env.user.partner_id.id,
					'model': 'asm.student',
					'res_id': wiz.student_id.id,
					'message_type': 'notification',
					'subtype_id': self.env.ref('mail.mt_note').id,
					'body': text,
	 			})

class ChangeClassStudentAdd(models.TransientModel):
	_name = "as.class_student.add"
	_description = "Add Class History"

	wizard_id = fields.Many2one("as.class_student.wiz", ondelete="cascade")
	class_id = fields.Many2one("asm.class", ondelete="restrict", string="Kelas", required=True)
	term_id = fields.Many2one("asm.term", ondelete="cascade", string="Tahun Ajaran", required=True)


class ChangeClassStudentEdit(models.TransientModel):
	_name = "as.class_student.edit"
	_description = "Add Class History"

	wizard_id = fields.Many2one("as.class_student.wiz", ondelete="cascade")
	student_id = fields.Many2one("asm.student", ondelete="set null", related="wizard_id.student_id", store=True, string="Siswa")
	class_student_id = fields.Many2one("as.class_student", ondelete="cascade", domain="[('student_id', '=', student_id)]")
	term_id = fields.Many2one("asm.term", ondelete="cascade", string="Tahun Ajaran")

	@api.onchange("class_student_id")
	def _get_term(self):
		for line in self:
			if line.class_student_id:
				line.term_id = line.class_student_id.term_id.id
