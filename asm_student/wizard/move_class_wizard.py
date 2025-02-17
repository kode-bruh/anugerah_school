from odoo import api, models, fields, exceptions
from datetime import date, datetime, timedelta

class MoveClassWizard(models.TransientModel):
	_name = "as.move_class.wiz"
	_description = "Wizard to Move Student Class"

	student_id = fields.Many2one("asm.student", ondelete="set null", string="Siswa")
	current_class = fields.Char(string="Kelas Saat Ini", related="student_id.current_class")
	next_class = fields.Many2one("asm.class", ondelete="set null", string="Kelas Berikutnya")
	year_in = fields.Integer(string="Tahun Awal", default=lambda *a: int(datetime.now().strftime("%Y")), help="Masukkan tahun siswa naik ke kelas ini.")
	year_out = fields.Integer(string="Tahun Akhir", default=lambda *a: int(datetime.now().strftime("%Y")) + 1, help="Masukkan tahun siswa akan naik dari kelas ini.")
	term_id = fields.Many2one("asm.term", ondelete="cascade", string="Tahun Ajaran", required=True)

	@api.onchange('year_in', 'year_out')
	def _validate_year(self):
		for wiz in self:
			if (wiz.year_in and wiz.year_out) and wiz.year_out <= wiz.year_in:
				raise exceptions.UserError("Tahun Awal tidak boleh lebih atau sama dengan Tahun Akhir.")

	@api.onchange('current_class', 'next_class')
	def _validate_class(self):
		for wiz in self:
			if len(wiz.student_id.student_class_ids) > 0:
				current_class = False
				if len(wiz.student_id.student_class_ids) > 0:
					current_class = sorted(wiz.student_id.student_class_ids, key=lambda i: i['class_id']['priority'])[-1].class_id
				if current_class and wiz.next_class:
					if current_class.priority > wiz.next_class.priority:
						raise exceptions.UserError("Tidak dapat memindahkan ke kelas yang lebih rendah.")

	def validate(self):
		for wiz in self:
			text = "Terdapat kesalahan data saat mengubah kelas:\n"
			valid = True
			if not wiz.student_id:
				valid = False
				text += "- SISWA wajib dipilih\n"
			if not wiz.next_class:
				valid = False
				text += "- KELAS BERIKUTNYA wajib dipilih\n"

			if valid:
				current_class = "Tidak Ada"
				if len(wiz.student_id.student_class_ids) > 0:
					current_class = sorted(wiz.student_id.student_class_ids, key=lambda i: i['class_id']['priority'])[-1].class_id.name
				wiz.student_id.student_class_ids = [(0, 0, {
					'class_id': wiz.next_class.id,
					'student_id': wiz.student_id.id,
					'term_id': wiz.term_id.id,
					'year_in': wiz.term_id.year_in,
					'year_out': wiz.term_id.year_out,
				})]

				# Create log
				timestamp = datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()), "%d %B %Y %H:%M")
				self.env['mail.message'].create({
					'subject': 'Class Changed',
					'date': datetime.now(),
					'author_id': self.env.user.partner_id.id,
					'model': 'asm.student',
					'res_id': wiz.student_id.id,
					'message_type': 'notification',
					'subtype_id': self.env.ref('mail.mt_note').id,
					'body': '<p>Siswa telah dipindahkan dari kelas <b>%s</b> ke <b>%s</b> oleh <b>%s</b> pada <b>%s</b></p>' % (current_class, wiz.next_class.display_name, self.env.user.partner_id.name, timestamp)
	 			})
			else:
				raise exceptions.UserError(text)

			