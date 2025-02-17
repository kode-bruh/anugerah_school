from odoo import api, models, fields, exceptions
from datetime import datetime, date, timedelta

class ClassStage(models.Model):
	_name = "asm.class.stage"
	_description = "Jenjang Kelas"

	name = fields.Many2one("as.selection", ondelete="restrict", string="Jenjang", required=True, domain="[('is_class_stage', '=', True)]")
	class_ids = fields.One2many("asm.class", "class_stage_id", readonly=True)

class Class(models.Model):
	_name = "asm.class"
	_description = "Kelas"

	class_stage_id = fields.Many2one("asm.class.stage", ondelete="restrict", string="Jenjang", required=True)
	name = fields.Char(string="Nama Kelas", compute="_get_name", store=True)
	stage = fields.Many2one("as.selection", ondelete="restrict", string="Kelas", required=True, domain="[('is_class_stage', '=', True)]")
	alt = fields.Many2one("as.selection", ondelete="restrict", string="Kelas", required=True, domain="[('is_class_alt', '=', True)]")
	priority = fields.Integer(string="Prioritas", required=True, help="Masukkan prioritas sesuai dengan angka kelas. \nContoh:\n- Nama Kelas XIIA - Prioritas 12\n- Nama Kelas IXB - Prioritas 9")
	note = fields.Char(string="Keterangan")

	@api.model
	def create(self, values):
		res = super(Class, self).create(values)
		res._validate_class_stage()
		return res

	def write(self, values):
		res = super(Class, self).write(values)
		for i in self:
			i._validate_class_stage()
		return res

	@api.onchange("class_stage_id")
	def _get_default_stage(self):
		for i in self:
			if i.class_stage_id:
				i.stage = i.class_stage_id.name.id

	def _validate_class_stage(self):
		for i in self:
			if i.class_stage_id.name.id != i.stage.id:
				raise exceptions.UserError("Jenjang kelas tidak sama. Diharap untuk memastikan jenjang di data 'KELAS' ini dan jenjang di field 'JENJANG' sama.")

	@api.depends("stage", "alt")
	def _get_name(self):
		for i in self:
			if i.stage and i.alt:
				i.name = "%s %s" % (i.stage.name, i.alt.name)
			else:
				i.name = "New"

class ClassStudent(models.Model):
	_name = "as.class_student"
	_description = "Kelas per Siswa"
	_rec_name = "class_id"

	class_id = fields.Many2one("asm.class", ondelete="restrict", string="Kelas", required=True)
	student_id = fields.Many2one("asm.student", ondelete="cascade", string="Siswa")
	year_in = fields.Integer(string="Tahun Awal", required=True, help="Masukkan tahun siswa naik ke kelas ini.")
	year_out = fields.Integer(string="Tahun Akhir", required=True, help="Masukkan tahun siswa akan naik dari kelas ini.")
	term_id = fields.Many2one("asm.term", ondelete="restrict", string="Tahun Ajaran")

	@api.onchange("year_in", "year_out")
	def _validate_semester(self):
		for i in self:
			if i.year_in and i.year_out:
				if i.year_in >= i.year_out:
					raise exceptions.UserError("Tahun awal harus selalu lebih awal dari tahun akhir. \nContoh:\n- Tahun Awal: 2020\n- Tahun Akhir: 2021\nUntuk tahun ajaran 2020-2021.")

	def _get_proper_term(self):
		for i in self:
			term = self.env['asm.term'].search([('year_in', '=', i.year_in), ('year_out', '=', i.year_out)], limit=1)
			if term:
				i.term_id = term.id

class StudentTransfer(models.Model):
	_name = "as.student_transfer"
	_description = "Perpindahan Kelas Siswa"

	name = fields.Char(string="Kode Transfer", readonly=True)
	allow_class_transfer = fields.Boolean(string="Transfer Massal")
	item_ids = fields.One2many("as.student_transfer_item", "transfer_id", string="List Perpindahan Kelas")
	validate_uid = fields.Many2one("res.users", ondelete="set null", string="Disahkan oleh", readonly=True)
	validate_date = fields.Datetime(string="Waktu Pengesahan", readonly=True)
	class_id = fields.Many2one("asm.class", ondelete="set null", string="Kelas")
	select_year_in = fields.Integer(string="Tahun Awal")
	select_year_out = fields.Integer(string="Tahun Akhir")
	select_term_id = fields.Many2one("asm.term", ondelete="set null", string="Tahun Ajaran")
	year_in = fields.Integer(string="Tahun Awal", help="Masukkan tahun siswa naik ke kelas ini.")
	year_out = fields.Integer(string="Tahun Akhir", help="Masukkan tahun siswa akan naik dari kelas ini.")
	term_id = fields.Many2one("asm.term", ondelete="restrict", string="Tahun Ajaran")
	state = fields.Selection([
		('Draft', 'Draft'),
		('Waiting', 'Waiting'),
		('Validated', 'Validated'),
		('Cancelled', 'Cancelled')
	], string="State", default="Draft")

	def populate_student_class(self):
		if not self.class_id:
			raise exceptions.UserError("Harap pilih kelas.")
		if not self.select_term_id:
			raise exceptions.UserError("Harap pilih tahun ajaran.")
		if not self.id:
			raise exceptions.UserError("Harap menyimpan record ini terlebih dahulu.")

		students = self.env['as.class_student'].search([('class_id', '=', self.class_id.id), ('term_id', '=', self.select_term_id.id)])
		self.item_ids = [(5, 0, 0)]

		for student in students:
			class_history = self.env['as.class_student'].search([('student_id', '=', student.student_id.id)])
			last_class = sorted(class_history, key=lambda i: i['class_id']['priority'])[-1]

			if last_class.class_id.id == self.class_id.id:
				self.item_ids = [(0, 0, {
					'transfer_id': self.id,
					'student_id': student.student_id.id,
				})]

	@api.onchange("year_in", "year_out")
	def _validate_semester(self):
		if self.year_in and self.year_out:
			if self.year_in >= self.year_out:
				raise exceptions.UserError("Tahun awal harus selalu lebih awal dari tahun akhir. \nContoh:\n- Tahun Awal: 2020\n- Tahun Akhir: 2021\nUntuk tahun ajaran 2020-2021.")

	@api.model
	def create(self, values):
		res = super(StudentTransfer, self).create(values)
		res['name'] = "AS/SC/TRF/%s" % str(res['id']).zfill(4)
		return res

	def action_confirm(self):
		if self.state == 'Draft':
			self.state = 'Waiting'

	def action_validate(self):
		for i in self:
			if i.state == 'Waiting':
				for item in i.item_ids:
					current_class = "Tidak Ada"
					if len(item.student_id.student_class_ids) > 0:
						current_class = sorted(item.student_id.student_class_ids, key=lambda i: i['class_id']['priority'])[-1].class_id.name
					item.class_student_id = self.env['as.class_student'].create({
						'class_id': item.next_class.id,
						'student_id': item.student_id.id,
						'year_in': i.term_id.year_in,
						'year_out': i.term_id.year_out,
						'term_id': i.term_id.id,
					})
					# Create log
					timestamp = datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()), "%d %B %Y %H:%M")
					self.env['mail.message'].create({
						'subject': 'Class Changed',
						'date': datetime.now(),
						'author_id': self.env.user.partner_id.id,
						'model': 'asm.student',
						'res_id': item.student_id.id,
						'message_type': 'notification',
						'subtype_id': self.env.ref('mail.mt_note').id,
						'body': '<p>Siswa telah dipindahkan dari kelas <b>%s</b> ke <b>%s</b> oleh <b>%s</b> pada <b>%s</b></p>' % (current_class, item.next_class.display_name, self.env.user.partner_id.name, timestamp)
		 			})

				i.state = 'Validated'
				i.validate_uid = self.env.uid
				i.validate_date = datetime.today()
				

	def action_draft(self):
		self.state = 'Draft'

	def action_cancel(self):
		for i in self.item_ids:
			if i.class_student_id:
				i.class_student_id.unlink()
		self.validate_uid = None
		self.validate_date = None
		self.state = 'Cancelled'

class StudentTransferItem(models.Model):
	_name = "as.student_transfer_item"
	_description = "Baris Perpindahan Kelas Siswa"

	transfer_id = fields.Many2one("as.student_transfer", ondelete="cascade", string="Kode Transfer")
	student_id = fields.Many2one("asm.student", ondelete="cascade", string="Siswa", required=True)
	current_class = fields.Char(string="Kelas Sekarang", compute="_get_current_class", store=True)
	next_class = fields.Many2one("asm.class", ondelete="restrict", string="Kelas Selanjutnya")
	class_student_id = fields.Many2one("as.class_student", ondelete="set null", string="Kelas Siwa")	

	@api.depends("student_id")
	def _get_current_class(self):
		for i in self:
			i.current_class = i.student_id.current_class