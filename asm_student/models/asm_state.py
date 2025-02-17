from odoo import api, fields, models
from datetime import datetime, date, timedelta

class State(models.Model):
	_name = "asm.state"
	_description = "Status Siswa"

	name = fields.Char(string="Deskripsi", required=True)
	default = fields.Boolean(string="Default")
	student_state = fields.Boolean(string="Data Siswa")

class StateTransfer(models.Model):
	_name = "as.state_transfer"
	_description = "Perpindahan Status Siswa"

	name = fields.Char(string="Kode Transfer", readonly=True)
	allow_state_transfer = fields.Boolean(string="Transfer Massal")
	state_id = fields.Many2one('asm.state', string="Status", domain="[('student_state', '=', True)]")
	item_ids = fields.One2many("as.state_transfer_item", "transfer_id", string="List Perpindahan Kelas")
	validate_uid = fields.Many2one("res.users", ondelete="set null", string="Disahkan oleh", readonly=True)
	validate_date = fields.Datetime(string="Waktu Pengesahan", readonly=True)
	state = fields.Selection([
		('Draft', 'Draft'),
		('Waiting', 'Waiting'),
		('Validated', 'Validated'),
		('Cancelled', 'Cancelled')
	], string="State", default="Draft")

	def populate_student_class(self):
		if not self.state_id:
			raise exceptions.UserError("Harap pilih status yang ingin diubah terlebih dahulu.")
		if not self.id:
			raise exceptions.UserError("Harap menyimpan record ini terlebih dahulu.")
		for student in self.item_ids:
			student.sudo().unlink()			
		students = self.env['asm.student'].search([('state_id', '=', self.state_id.id), ('active', '=', True)])
		for student in students:
			item = self.env['as.state_transfer_item'].sudo().create({	
				'transfer_id': self.id,
				'student_id': student.id,
			})

	@api.model
	def create(self, values):
		res = super(StateTransfer, self).create(values)
		res['name'] = "AS/SS/TRF/%s" % str(res['id']).zfill(4)
		return res

	def action_confirm(self):
		if self.state == 'Draft':
			self.state = 'Waiting'

	def action_validate(self):
		for i in self:
			if i.state == 'Waiting':
				for item in i.item_ids:
					item.student_id.state_id = item.next_state.id
					# Create log
					self.env['mail.message'].create({
						'subject': 'State Changed',
						'date': datetime.now(),
						'author_id': self.env.user.partner_id.id,
						'model': 'asm.student',
						'res_id': item.student_id.id,
						'message_type': 'notification',
						'subtype_id': self.env.ref('mail.mt_note').id,
						'body': '<p>Siswa telah dipindahkan dari status <b>%s</b> ke <b>%s</b> oleh <b>%s</b> pada <b>%s</b></p>' % (item.current_state.display_name, item.next_state.display_name, self.env.user.partner_id.name, datetime.now().strftime("%d %B %Y %H:%M"))
		 			})
				i.state = 'Validated'
				i.validate_uid = self.env.uid
				i.validate_date = datetime.today()

	def action_draft(self):
		self.state = 'Draft'

	def action_cancel(self):
		for i in self.item_ids:
			i.student_id.state_id = i.current_state.id
		self.validate_uid = None
		self.validate_date = None
		self.state = 'Cancelled'

class StateTransferItem(models.Model):
	_name = "as.state_transfer_item"
	_description = "Baris Perpindahan Status Siswa"

	transfer_id = fields.Many2one("as.state_transfer", ondelete="cascade", string="Kode Transfer")
	student_id = fields.Many2one("asm.student", ondelete="cascade", string="Siswa", required=True)
	current_class = fields.Char(string="Kelas", related="student_id.current_class", readonly=True)
	current_state = fields.Many2one("asm.state", ondelete="cascade", string="Status Sekarang", compute="_get_current_state", store=True)
	next_state = fields.Many2one("asm.state", ondelete="restrict", string="Status Berikutnya", required=True, domain="[('student_state', '=', True)]")

	@api.depends("student_id")
	def _get_current_state(self):
		for i in self:
			i.current_state = i.student_id.state_id.id